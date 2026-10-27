"""
jetson_find_object.py — Jetson 에서 돌아가는 "미니 물건 찾기" (카메라 + detectNet + CLIP 기억/검색)

[왜 필요한가]
  물건 찾기 로봇의 비전 파트를 로봇 없이 먼저 완성해 보는 단계.
  로봇이 생기면 "화면 위치" 대신 "지도 좌표"를 저장하도록 바꾸기만 하면 된다.

[흐름]
  카메라 영상 → detectNet 으로 물체 상자 검출 (수업 실습과 같음, 브라우저로 실시간 확인)
  s 입력  → 지금 화면에서 검출된 물체들을 잘라 CLIP 벡터로 "기억" (= 로봇의 순찰)
  t 입력  → 화면을 3x3 조각으로 잘라 기억 (detectNet 이 모르는 물건도 기억하려고)
  q 문장  → 기억 중 문장과 가장 비슷한 물체를 찾아 (= 사용자 질문)
            브라우저 화면에 그 물체가 있던 위치를 5초간 표시 + 결과 사진 저장

[입력]  --input  카메라 (기본 v4l2:///dev/video0)
        --output 영상 출력 (기본 webrtc://@:8554/mystream → 브라우저 http://<JETSON-IP>:8554)
        터미널 명령: s / t / q <문장> / l / x / h / exit
[출력]  브라우저 영상, 터미널 검색 결과, memory/ 폴더 (기억 파일, 잘라낸 사진, result.jpg)

[연결]  vision/clip_jetson_test.py 로 확인한 CLIP 설정(ViT-B-32, FP16)을 그대로 쓴다.
        ir-guide 의 simple_mobilenet.py 와 같은 videoSource/videoOutput 설정을 쓴다.

[실행]  (Jetson)
  conda activate test1001
  cd ~/uos_ir/vision
  python jetson_find_object.py
  → 노트북 브라우저에서 http://192.168.1.206:8554 를 열고, 터미널에 s, q a cup 처럼 입력
"""
import argparse
import os
import sys
import threading
import time

import numpy as np
import open_clip
import torch
from PIL import Image

from jetson_inference import detectNet
from jetson_utils import (cudaDeviceSynchronize, cudaDrawRect, cudaFont,
                          cudaToNumpy, videoOutput, videoSource)

HERE = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(HERE, "memory")
CROP_DIR = os.path.join(MEM_DIR, "crops")
MEM_FILE = os.path.join(MEM_DIR, "memory.npz")
os.makedirs(CROP_DIR, exist_ok=True)

HELP = """
명령어 (입력 후 Enter):
  s            지금 화면의 검출 물체들을 기억
  t            지금 화면을 3x3 조각으로 잘라 기억 (detectNet 이 모르는 물건용)
  q <문장>     기억에서 찾기   예) q a cup   /  q a black bag  /  q a plastic cup with a straw
               (※ 저장해 둔 기억을 찾는 것. 물건/카메라를 옮겼으면 다시 s, t 로 저장해야 반영됨)
  f <문장>     지금 화면에서 바로 찾기 (기억 저장 없이, 겹치는 창 34개 + 검출 상자, 1~2초 걸림)
  l            기억 목록 보기
  x            기억 모두 지우기
  h            도움말
  exit         종료 (또는 Ctrl+C)
"""


# ---------------------------------------------------------------- 기억 저장소
class Memory:
    """
    물체 기억 하나 = CLIP 벡터 + 화면 상자(l,t,r,b) + 라벨 + 저장 시각 + 잘라낸 사진 경로.
    로봇 버전에서는 '화면 상자' 대신 '지도 좌표 (x, y)' 를 저장하게 된다.
    """

    def __init__(self):
        self.vecs, self.boxes, self.labels, self.times, self.paths = [], [], [], [], []
        if os.path.exists(MEM_FILE):
            d = np.load(MEM_FILE, allow_pickle=True)
            self.vecs = list(d["vecs"])
            self.boxes = [tuple(b) for b in d["boxes"]]
            self.labels = list(d["labels"])
            self.times = list(d["times"])
            self.paths = list(d["paths"])
            print("이전 기억 {}개를 불러왔습니다.".format(len(self.vecs)))

    def add(self, vec, box, label, crop_rgb):
        """기억 하나 추가. 입력: vec(512), box(l,t,r,b), label, crop_rgb(잘라낸 사진 numpy RGB)"""
        path = os.path.join(CROP_DIR, "{}_{}.jpg".format(int(time.time() * 1000), len(self.vecs)))
        Image.fromarray(crop_rgb).save(path, quality=90)
        self.vecs.append(vec)
        self.boxes.append(tuple(int(v) for v in box))
        self.labels.append(label)
        self.times.append(time.time())
        self.paths.append(path)

    def save(self):
        np.savez(MEM_FILE, vecs=np.array(self.vecs), boxes=np.array(self.boxes), labels=np.array(self.labels),
                 times=np.array(self.times), paths=np.array(self.paths))

    def clear(self):
        self.vecs, self.boxes, self.labels, self.times, self.paths = [], [], [], [], []
        if os.path.exists(MEM_FILE):
            os.remove(MEM_FILE)


# ---------------------------------------------------------------- CLIP
class Clip:
    """CLIP (ViT-B-32, FP16) 를 GPU 에 올려두고 사진/문장을 벡터로 바꾼다."""

    def __init__(self):
        print("CLIP 불러오는 중... (약 15초)")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k")
        self.tokenizer = open_clip.get_tokenizer("ViT-B-32")
        self.model = self.model.to("cuda").eval().half()

    @torch.no_grad()
    def images(self, crops_rgb):
        """잘라낸 사진 목록(numpy RGB) → (N, 512) 정규화 벡터"""
        x = torch.stack([self.preprocess(Image.fromarray(c)) for c in crops_rgb]).to("cuda").half()
        f = self.model.encode_image(x)
        return (f / f.norm(dim=-1, keepdim=True)).float().cpu().numpy()

    @torch.no_grad()
    def text(self, sentence):
        """문장 → (512,) 정규화 벡터"""
        f = self.model.encode_text(self.tokenizer([sentence]).to("cuda"))
        return (f / f.norm(dim=-1, keepdim=True)).float().cpu().numpy()[0]


# ---------------------------------------------------------------- 자르기
def detection_crops(frame_rgb, detections, net, pad=0.1):
    """
    detectNet 결과 상자대로 사진을 자른다 (상자를 10% 넓혀서 물체가 덜 잘리게).
    입력: frame_rgb — 오버레이 그리기 전의 깨끗한 화면(numpy), detections — net.Detect 결과
    출력: [(조각 사진, (l,t,r,b), 라벨), ...]
    """
    h, w = frame_rgb.shape[:2]
    out = []
    for d in detections:
        pw, ph = (d.Right - d.Left) * pad, (d.Bottom - d.Top) * pad
        l, t = int(max(0, d.Left - pw)), int(max(0, d.Top - ph))
        r, b = int(min(w, d.Right + pw)), int(min(h, d.Bottom + ph))
        if r - l > 10 and b - t > 10:
            out.append((frame_rgb[t:b, l:r].copy(), (l, t, r, b), net.GetClassDesc(d.ClassID)))
    return out


def grid_crops(frame_rgb, n=3):
    """화면을 n x n 조각으로 자른다. 출력 형식은 detection_crops 와 같음."""
    h, w = frame_rgb.shape[:2]
    out = []
    for r in range(n):
        for c in range(n):
            l, t, rr, b = c * w // n, r * h // n, (c + 1) * w // n, (r + 1) * h // n
            out.append((frame_rgb[t:b, l:rr].copy(), (l, t, rr, b), "tile{}{}".format(r, c)))
    return out


def sliding_crops(frame_rgb, sizes=(2, 3)):
    """
    여러 크기의 창을 반씩 겹치게 밀면서 자른다 (물건이 조각 경계에서 잘리지 않도록).
    sizes=(2, 3): 화면의 1/2 크기 창 3x3=9개 + 1/3 크기 창 5x5=25개 = 34개
    출력 형식은 grid_crops 와 같음.
    """
    h, w = frame_rgb.shape[:2]
    out = []
    for n in sizes:
        cw, ch = w // n, h // n
        sx, sy = cw // 2, ch // 2          # 반 칸씩 이동 → 50% 겹침
        for t in range(0, h - ch + 1, sy):
            for l in range(0, w - cw + 1, sx):
                out.append((frame_rgb[t:t + ch, l:l + cw].copy(), (l, t, l + cw, t + ch), "win{}".format(n)))
    return out


# 배경 문장: 질의 문장이 이것들보다 "확실히" 더 맞는 창을 고르기 위한 경쟁 상대
BACKGROUND_PROMPTS = [
    "a photo of a wall", "a photo of the floor", "a photo of a ceiling", "a photo of a desk",
    "a photo of a chair", "a photo of a person", "a photo of a computer monitor",
    "a photo of a keyboard", "a blurry photo of a room",
]


def live_scores(clip, vecs, query):
    """
    각 창이 '배경 문장들보다 질의 문장에 더 가까운 정도'를 확률(0~1)로 계산한다.
    = CLIP 의 zero-shot 분류 방식: [질의, 배경1, 배경2, ...] 중 무엇인지 softmax
    입력: vecs — (N, 512) 창 벡터, query — 찾는 문장
    출력: (확률 배열, 질의와의 원래 유사도 배열)
    """
    texts = [query] + [p for p in BACKGROUND_PROMPTS if p.lower() not in query.lower()]
    tvecs = np.stack([clip.text(t) for t in texts])          # (K, 512)
    logits = 100.0 * vecs @ tvecs.T                          # (N, K), CLIP 기본 온도 100
    logits -= logits.max(axis=1, keepdims=True)
    probs = np.exp(logits)
    probs /= probs.sum(axis=1, keepdims=True)
    return probs[:, 0], vecs @ tvecs[0]


def save_crops_image(crops_rgb, name):
    """조각 사진들을 옆으로 붙여 memory/<name> 으로 저장"""
    tiles = [Image.fromarray(c).resize((240, max(1, int(240 * c.shape[0] / c.shape[1])))) for c in crops_rgb]
    canvas = Image.new("RGB", (240 * len(tiles), max(t.height for t in tiles)), (40, 40, 40))
    for k, t in enumerate(tiles):
        canvas.paste(t, (240 * k, 0))
    path = os.path.join(MEM_DIR, name)
    canvas.save(path, quality=90)
    return path


def age_text(t):
    """저장 시각 → '35초 전', '4분 전' 같은 글자"""
    sec = int(time.time() - t)
    if sec < 60:
        return "{}초 전".format(sec)
    if sec < 3600:
        return "{}분 전".format(sec // 60)
    return "{}시간 전".format(sec // 3600)


def save_result_image(memory, results, query):
    """검색 결과 Top-3 조각을 옆으로 붙여 memory/result.jpg 로 저장 (VS Code 에서 열어볼 수 있음)."""
    tiles = []
    for sim, i in results:
        im = Image.open(memory.paths[i]).convert("RGB")
        im = im.resize((240, max(1, int(240 * im.height / im.width))))
        tiles.append(im)
    H = max(t.height for t in tiles)
    canvas = Image.new("RGB", (240 * len(tiles), H), (40, 40, 40))
    for k, t in enumerate(tiles):
        canvas.paste(t, (240 * k, 0))
    path = os.path.join(MEM_DIR, "result.jpg")
    canvas.save(path, quality=90)
    return path


# ---------------------------------------------------------------- 터미널 입력 (별도 스레드)
class Commands:
    """영상이 계속 돌아가는 동안 터미널 입력을 따로 받아 큐에 쌓는다."""

    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                line = sys.stdin.readline()
            except Exception:
                return
            if not line:
                return
            with self.lock:
                self.queue.append(line.strip())

    def pop(self):
        with self.lock:
            return self.queue.pop(0) if self.queue else None


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="v4l2:///dev/video0")
    ap.add_argument("--output", default="webrtc://@:8554/mystream")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--network", default="ssd-mobilenet-v2")
    ap.add_argument("--threshold", type=float, default=0.5)
    args = ap.parse_args()

    clip = Clip()
    memory = Memory()
    net = detectNet(args.network, argv=[], threshold=args.threshold)
    # 수업 예제(simple_mobilenet.py)와 똑같은 입력 옵션
    inp = videoSource(args.input, options={"width": args.width, "height": args.height,
                                           "codec": "mjpeg", "encoder": "v4l2"})
    out = videoOutput(args.output, options={"codec": "h264", "encoder": "v4l2", "bitrate": 8000000, "latency": 30})
    font = cudaFont()
    cmds = Commands()

    print(HELP)
    print("브라우저에서 http://<JETSON-IP>:8554 를 열어 영상을 확인하세요.")

    try:
        run_loop(args, clip, memory, net, inp, out, font, cmds)
    except KeyboardInterrupt:
        pass
    except Exception:
        import traceback
        traceback.print_exc()
        print("\n오류로 종료합니다. 위의 Traceback 을 보여주세요.")
    # 영상 서버 스레드가 남아 프로그램이 안 꺼지는 것을 막기 위해 강제 종료
    sys.stdout.flush()
    os._exit(0)


def run_loop(args, clip, memory, net, inp, out, font, cmds):
    """영상 한 장씩: 명령 처리 → 캡처 → (저장) → 검출 → (검색 결과 표시) → 출력"""
    highlight = None  # (box, 표시할 글자, 끝나는 시각)
    pending = None    # 다음 프레임에서 처리할 저장 명령 ('s' 또는 't')
    frames, last_report, empty = 0, time.time(), 0

    while True:
        cmd = cmds.pop()
        if cmd:
            if cmd in ("exit", "quit"):
                print("종료합니다.")
                return
            elif cmd in ("s", "t"):
                pending = cmd
            elif cmd == "l":
                if not memory.vecs:
                    print("기억이 비어 있습니다.")
                for i, (lab, box) in enumerate(zip(memory.labels, memory.boxes)):
                    print("  #{:02d} {:12s} 위치 {}".format(i, lab, box))
            elif cmd == "x":
                memory.clear()
                print("기억을 모두 지웠습니다.")
            elif cmd.startswith("q "):
                query = cmd[2:].strip()
                if not memory.vecs:
                    print("기억이 비어 있습니다. 먼저 s 또는 t 로 저장하세요.")
                else:
                    sims = np.array(memory.vecs) @ clip.text(query)
                    order = list(np.argsort(-sims)[:3])
                    results = [(float(sims[i]), int(i)) for i in order]
                    print("'{}' 기억 검색 결과 (※ 지금 화면이 아니라 저장된 기억 기준):".format(query))
                    for rank, (s, i) in enumerate(results, 1):
                        print("  #{} 유사도 {:.3f}  {:12s} 위치 {}  ({} 기억)".format(
                            rank, s, memory.labels[i], memory.boxes[i], age_text(memory.times[i])))
                    print("  결과 사진:", save_result_image(memory, results, query))
                    best = results[0][1]
                    highlight = (memory.boxes[best], "MEMORY: {} ({:.2f}, {})".format(
                        query, results[0][0], age_text(memory.times[best])), time.time() + 5)
            elif cmd.startswith("f "):
                pending = ("f", cmd[2:].strip())
            elif cmd in ("h", "help"):
                print(HELP)
            else:
                print("모르는 명령입니다. h 를 입력하면 도움말이 나옵니다.")

        img = inp.Capture()
        if img is None:
            empty += 1
            if empty % 5 == 0:
                print("[진단] 카메라에서 영상이 안 들어옵니다 ({}번째). 카메라 번호/다른 프로그램 사용 여부 확인".format(empty))
            continue
        frames += 1
        if frames == 1:
            print("[진단] 첫 영상 수신: {}x{} → 이제 브라우저를 새로고침하세요".format(img.width, img.height))
        if time.time() - last_report > 15:
            print("[진단] 영상 {}장 처리 중, detectNet {:.0f} FPS".format(frames, net.GetNetworkFPS()))
            last_report = time.time()

        # 저장 명령이 있으면, 상자를 그리기 '전'의 깨끗한 화면을 복사해 둔다
        clean = None
        if pending:
            cudaDeviceSynchronize()
            clean = cudaToNumpy(img)[:, :, :3].copy()

        detections = net.Detect(img, overlay="box,labels,conf")

        if isinstance(pending, tuple) and clean is not None:
            # f: 지금 화면에서 바로 찾기 (기억에는 저장 안 함)
            query = pending[1]
            t0 = time.time()
            crops = detection_crops(clean, detections, net) + sliding_crops(clean)
            vecs = clip.images([c[0] for c in crops])
            score, sims = live_scores(clip, vecs, query)
            order = list(np.argsort(-score)[:3])
            print("'{}' 지금 화면 검색 결과 ({}개 창, {:.1f}초):".format(query, len(crops), time.time() - t0))
            for rank, i in enumerate(order, 1):
                print("  #{} 확률 {:.2f} (유사도 {:.3f})  {:12s} 위치 {}".format(
                    rank, float(score[i]), float(sims[i]), crops[i][2], crops[i][1]))
            print("  결과 사진:", save_crops_image([crops[i][0] for i in order], "result_now.jpg"))
            best = order[0]
            highlight = (crops[best][1], "NOW: {} ({:.2f})".format(query, float(score[best])), time.time() + 5)
            pending = None
        elif pending and clean is not None:
            crops = detection_crops(clean, detections, net) if pending == "s" else grid_crops(clean)
            if crops:
                vecs = clip.images([c[0] for c in crops])
                for (crop, box, label), vec in zip(crops, vecs):
                    memory.add(vec, box, label, crop)
                memory.save()
                print("{}개 기억 추가: {}  (총 {}개)".format(len(crops), [c[2] for c in crops], len(memory.vecs)))
            else:
                print("검출된 물체가 없습니다. t 로 조각 저장을 해보세요.")
            pending = None

        # 검색 결과를 5초간 화면에 표시
        if highlight and time.time() < highlight[2]:
            l, t, r, b = highlight[0]
            cudaDrawRect(img, (l, t, r, b), (255, 0, 255, 70))
            font.OverlayText(img, img.width, img.height, highlight[1], l + 5, t + 5, font.White, font.Gray40)
        font.OverlayText(img, img.width, img.height, "memory: {}".format(len(memory.vecs)),
                         10, img.height - 40, font.White, font.Gray40)

        out.Render(img)
        out.SetStatus("find-object | {:.0f} FPS".format(net.GetNetworkFPS()))
        if not inp.IsStreaming() or not out.IsStreaming():
            print("영상 입력/출력이 끝나서 종료합니다.")
            return


if __name__ == "__main__":
    main()

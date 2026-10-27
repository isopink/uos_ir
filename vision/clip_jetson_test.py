"""
clip_jetson_test.py — Jetson 에서 CLIP 이 돌아가는지, 얼마나 빠른지, 메모리를 얼마나 쓰는지 확인

[왜 필요한가]
  물건 찾기 로봇의 핵심은 CLIP (사진 ↔ 문장 비교) 이다.
  노트북(RTX 4060)에서는 잘 돌았지만, Jetson Xavier NX (GPU 메모리 공유 8GB, Python 3.8) 에서도
  실시간에 가깝게 돌아가는지 확인해야 YOLO/detectNet 과 같이 쓸 수 있다.

[하는 일]
  1. CLIP (ViT-B-32) 모델을 GPU 에 올린다 (처음엔 인터넷에서 약 600MB 다운로드)
  2. 사진 폴더의 이미지들을 CLIP 벡터로 바꾸며 1장당 처리 시간(ms)을 잰다
  3. 문장 질의("an orange", "a dog" ...)로 가장 비슷한 사진을 찾는다 (= 물건 찾기의 검색 단계)
  4. GPU 메모리 사용량을 출력한다

[입력]  --images 사진 폴더 (기본: jetson-inference 예제 사진 폴더)
        --fp16   반정밀도(FP16)로 실행 → 보통 더 빠르고 메모리도 덜 씀
[출력]  터미널: 모델 로딩 시간, 이미지 1장당 시간, 질의별 Top-3 결과, 메모리 사용량

[실행]  (Jetson, test1001 환경에서)
  conda activate test1001
  cd ~/uos_ir/vision
  python clip_jetson_test.py
  python clip_jetson_test.py --fp16          ← 둘을 비교해서 보고서에 쓰기

※ Python 3.8 (Jetson) 에서도 돌아가도록 최신 문법은 쓰지 않았다.
"""
import argparse
import glob
import os
import time

import torch
from PIL import Image

import open_clip

DEFAULT_IMAGES = os.path.expanduser("~/jetson-inference/build/aarch64/bin/images")
DEFAULT_QUERIES = [
    "an orange",
    "a banana",
    "a dog",
    "a cat",
    "a bird",
    "a car",
    "a person",
    "a red object",
]


def find_images(folder, limit):
    """
    폴더에서 사진 파일 목록을 찾는다.
    입력: folder — 사진 폴더, limit — 최대 몇 장
    출력: 파일 경로 목록
    """
    paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        paths += glob.glob(os.path.join(folder, ext))
    return sorted(paths)[:limit]


def gpu_mem_mb():
    """지금 PyTorch 가 GPU 에서 쓰고 있는 메모리(MB)와, 지금까지의 최대치(MB)."""
    return torch.cuda.memory_allocated() / 2**20, torch.cuda.max_memory_allocated() / 2**20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=DEFAULT_IMAGES, help="사진 폴더")
    ap.add_argument("--limit", type=int, default=40, help="최대 사진 수")
    ap.add_argument("--model", default="ViT-B-32")
    ap.add_argument("--pretrained", default="laion2b_s34b_b79k")
    ap.add_argument("--fp16", action="store_true", help="FP16(반정밀도)로 실행")
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print("CUDA 를 쓸 수 없습니다. conda activate test1001 을 했는지 확인하세요.")
        return
    device = "cuda"
    print("GPU:", torch.cuda.get_device_name(0))
    print("torch", torch.__version__, "| open_clip", open_clip.__version__)

    # ---- 1. 모델 불러오기
    t0 = time.time()
    model, _, preprocess = open_clip.create_model_and_transforms(args.model, pretrained=args.pretrained)
    tokenizer = open_clip.get_tokenizer(args.model)
    model = model.to(device).eval()
    if args.fp16:
        model = model.half()
    torch.cuda.synchronize()
    print("\n[1] 모델 로딩: {:.1f}초  ({} / {} / {})".format(
        time.time() - t0, args.model, args.pretrained, "FP16" if args.fp16 else "FP32"))
    print("    GPU 메모리(모델만): {:.0f} MB".format(gpu_mem_mb()[0]))

    # ---- 2. 사진 → 벡터 (시간 측정)
    paths = find_images(args.images, args.limit)
    if not paths:
        print("사진을 찾지 못했습니다:", args.images)
        print("--images 로 사진 폴더를 지정하세요.")
        return
    dtype = torch.float16 if args.fp16 else torch.float32

    def embed_image(path):
        """사진 1장 → 길이 1로 정규화된 CLIP 벡터"""
        x = preprocess(Image.open(path).convert("RGB")).unsqueeze(0).to(device, dtype)
        with torch.no_grad():
            f = model.encode_image(x)
        return f / f.norm(dim=-1, keepdim=True)

    # 워밍업: 처음 몇 번은 GPU 준비 때문에 느리므로 측정에서 뺀다
    for p in paths[:3]:
        embed_image(p)
    torch.cuda.synchronize()

    feats, times = [], []
    for p in paths:
        t = time.time()
        feats.append(embed_image(p))
        torch.cuda.synchronize()
        times.append((time.time() - t) * 1000)
    feats = torch.cat(feats)
    avg = sum(times) / len(times)
    print("\n[2] 사진 {}장 임베딩: 1장당 평균 {:.1f} ms  (≈ {:.1f} 장/초)".format(len(paths), avg, 1000 / avg))

    # ---- 3. 문장으로 검색
    print("\n[3] 문장 검색 (Top-3, 숫자 = 코사인 유사도)")
    with torch.no_grad():
        tok = tokenizer(DEFAULT_QUERIES).to(device)
        t = time.time()
        tfeat = model.encode_text(tok)
        torch.cuda.synchronize()
        text_ms = (time.time() - t) * 1000 / len(DEFAULT_QUERIES)
        tfeat = tfeat / tfeat.norm(dim=-1, keepdim=True)
        sims = (tfeat @ feats.T).float().cpu()
    for q, row in zip(DEFAULT_QUERIES, sims):
        top = row.topk(min(3, len(paths)))
        hits = ", ".join("{} ({:.2f})".format(os.path.basename(paths[i]), s) for s, i in zip(top.values, top.indices))
        print("  '{}': {}".format(q, hits))
    print("    문장 1개 임베딩: 평균 {:.1f} ms".format(text_ms))

    # ---- 4. 메모리
    now, peak = gpu_mem_mb()
    print("\n[4] GPU 메모리 (PyTorch 기준): 현재 {:.0f} MB / 최대 {:.0f} MB".format(now, peak))
    print("    ※ Jetson 은 CPU·GPU 가 메모리 8GB 를 같이 쓴다. 전체 사용량은 다른 터미널에서 jtop 으로 확인")

    print("\n=== 보고서용 요약 ===")
    print("모델 {} ({}), {}: 이미지 {:.1f} ms/장, 텍스트 {:.1f} ms/문장, 최대 GPU 메모리 {:.0f} MB".format(
        args.model, args.pretrained, "FP16" if args.fp16 else "FP32", avg, text_ms, peak))


if __name__ == "__main__":
    main()

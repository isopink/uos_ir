# 지능형로봇 (UOS IR)

시립대 2026-2학기 지능형로봇 수업 노트 및 실습 정리.

## 일정

| 일자 | 내용 |
|------|------|
| 10/1 | 수업 + 실습 (Jetson 환경 구성) |
| 10/8 | 수업 + 실습 |
| 12/3 | 프로젝트 데모 |
| 12/10 | 프로젝트 결과 발표 |
| 12/17 | 기말고사 실습 소개 |

## 실습 주제 (소개된 항목)

- 인터넷 스트리밍 (Streaming via internet)
- VSLAM (Visual Simultaneous Localization and Mapping)
- 실제 모바일 로봇 (Real-world mobile robot)

### 프로젝트 주제 선정 시 유의점

- 너무 쉬운 task는 피한다 (딥러닝 없는 단순 이미지 처리 등)
- 단순 구현은 지양하고, 발전 과정을 보여준다
- 컴퓨터 자원(메모리) 문제를 고려한다

## 실습 장비: NVIDIA Jetson

- 모델: ASUS PE1000N (Xavier NX)
- CPU: 6-core NVIDIA Carmel ARM 64-bit
- GPU: 384-core Volta + 48 Tensor Cores
- RAM: 8GB LPDDR4x
- OS: Ubuntu + NVIDIA JetPack

### 10/1 실습 순서

1. VSCode 설치
2. SSH 접속
3. [ir-guide](https://github.com/intMinsu/ir-guide) 환경 설정
4. Conda 환경 구성

필요 패키지: `nvpmodel`, `jetson_clocks`, GitHub CLI(`gh`), `jtop`, `nvidia-jetpack`, OpenCV(CUDA), FFmpeg, GStreamer, DeepStream

환경 확인 명령어:

```bash
cat /proc/device-tree/model     # 보드 모델
nvpmodel -q                     # 현재 전원 모드
which python3; python3 --version
python -c "import cv2; print(cv2.__version__, cv2.cuda.getCudaEnabledDeviceCount())"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

## 학습 메모

### SSH / 리눅스 기본 명령어

- `ls`: 현재 디렉토리 목록 (`ls .` 현재, `ls ..` 상위)
- `pwd`: 현재 경로
- `cd <dir>`: 이동 (`cd ~`: 홈 디렉토리)
- `clear`: 화면 정리

### TODO

- [ ] Linux, Ubuntu 공부하기
- [ ] 아이디어 회의, 와플파이 사용 예정 체크
- [ ] 노션 6번, 영상 3번
- [ ] scripts는 ir-guide 안에

## 강의 자료

`강의 자료/` 폴더 (로컬에만 보관, 저장소에는 미포함)

- IR_L01_Introduction
- IR_L02_Linear Algebra
- IR_L03_ProbabilisticRobotics

## 참고 링크

- [수업 가이드 (Notion)](https://feline-turret-112.notion.site/ac39978be31a47f186f408f930e21caa)
- [ir-guide (GitHub)](https://github.com/intMinsu/ir-guide)

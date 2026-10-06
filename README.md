# 지능형로봇 (UOS IR)

시립대 2026-2학기 지능형로봇 수업 노트 및 실습 정리.

## 일정

기준: `강의 자료/IR_L01_Introduction.pdf` (Course Schedule, Project Schedule)

### 주차별 수업

| 주차 | 일자 | 내용 |
|------|------|------|
| 1 | 9/3 | Introduction |
| 2 | 9/10 | Linear Algebra and Homogeneous Coordinates |
| 3 | 9/17 | Probabilistic Robotics |
| 4 | 9/24 | Project Guidelines (동영상, 추석) |
| 5 | 10/1 | Motion Models + 프로젝트 실습 |
| 6 | 10/8 | Sensor Models + 프로젝트 실습 |
| 7 | 10/15 | Occupancy Grid Maps |
| 8 | 10/22 | 중간고사 |
| 9 | 10/29 | Kalman Filter and EKF Localization |
| 10 | 11/5 | Particle Filter and SLAM Intro |
| 11 | 11/12 | EKF SLAM and FastSLAM |
| 12 | 11/19 | Graph-based SLAM (동영상, 출장) + 프로젝트 실습(자율) |
| 13 | 11/26 | Project Demo Day (교수평가) |
| 14 | 12/3 | Project Presentation (동료평가) |
| 15 | 12/10 | 기말고사 |
| 16 | 12/17 | 휴강 |

### 프로젝트 마감

| 일자 | 내용 |
|------|------|
| 9/17 | 조편성 완료 (2인 1조) |
| 10/1, 10/8 | 프로젝트 실습 수업 |
| 10/15 | 실습완료 보고서 제출 |
| 10/29 | 중간보고서 제출 |
| 11/26 | Project Demo |
| 12/3 | Project Presentation |
| 12/10 | 결과보고서 제출 |

> 확인 필요: 10/1 실습 슬라이드에는 데모 12/3, 결과 발표 12/10, 기말고사 12/17로 적혀 있어 위 일정과 일주일씩 다르다.

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

## 참고 링크

- [수업 가이드 (Notion)](https://feline-turret-112.notion.site/ac39978be31a47f186f408f930e21caa)
- [ir-guide (GitHub)](https://github.com/intMinsu/ir-guide)

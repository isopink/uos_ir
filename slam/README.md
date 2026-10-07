# SLAM (ROS 2 + TurtleBot3 Waffle Pi)

기획안 0단계 목표: **와플파이 LiDAR로 지도 만들기** (~10/15 실습완료 보고서).

- ROS 2 **Humble** (Ubuntu 22.04)
- SLAM: `slam_toolbox` (기본), `cartographer` (TurtleBot3 공식 예제) — 두 결과를 비교해서 보고서에 사용
- 운영 방식: 집에서 Gazebo 시뮬레이션으로 개발 → push → 실습실에서 pull 후 실제 로봇으로 검증

> 와플파이에 깔린 ROS 2 버전을 먼저 확인해야 합니다. Humble이 아니면 `scripts/env.sh`의 `ROS_DISTRO`와 설치 스크립트를 그 버전에 맞추세요. 로봇과 PC의 배포판이 다르면 통신이 안 됩니다.

## 폴더 구성

```
slam/
├── scripts/
│   ├── env.sh                  공통 환경 변수 (ROS_DOMAIN_ID, 로봇 모델 등)
│   ├── install_ros2_humble.sh  ROS 2 + TurtleBot3 + SLAM 패키지 설치
│   ├── sim_slam.sh             [집] Gazebo 시뮬레이션 SLAM
│   ├── save_map.sh             지도 저장 → maps/
│   ├── robot_bringup.sh        [와플파이] 센서·모터 시작
│   ├── verify_stage0.sh        [실습실] 실제 로봇 SLAM 검증 + rosbag 녹화
│   └── replay_bag.sh           [집] 녹화한 rosbag 으로 SLAM 재실행
├── maps/                       저장된 지도 (.pgm, .yaml) — Git에 올림
├── bags/                       rosbag — Git 제외 (용량 큼, 구글 드라이브로 공유)
└── logs/                       검증 로그 — Git 제외
```

## 1. 집 노트북 준비 (Windows → WSL2)

PowerShell을 **관리자 권한**으로 열고:

```powershell
wsl --install -d Ubuntu-22.04
```

- 재부팅 후 Ubuntu 사용자 이름/비밀번호를 설정합니다.
- "가상화를 사용하도록 설정" 오류가 나면 BIOS에서 Intel VT-x / AMD SVM을 켜세요.
- Windows 11은 WSLg가 기본이라 Gazebo, RViz 창이 그대로 뜹니다.

Ubuntu 터미널에서 이 저장소를 받고 설치합니다:

```bash
git clone https://github.com/isopink/uos_ir.git ~/uos_ir
cd ~/uos_ir/slam
./scripts/install_ros2_humble.sh
source ~/.bashrc
```

> 저장소는 WSL 안(`~/uos_ir`)에 clone 하세요. Windows 폴더(`/mnt/c/...`)에서 돌리면 느리고 권한 문제가 생깁니다.

## 2. 시뮬레이션으로 SLAM (집)

터미널 1 — Gazebo + SLAM + RViz:

```bash
./scripts/sim_slam.sh slam_toolbox world     # 또는: cartographer house
```

터미널 2 — 키보드로 로봇 조종 (`w/x` 전후, `a/d` 회전, `s` 정지):

```bash
ros2 run turtlebot3_teleop teleop_keyboard
```

지도가 다 그려지면 터미널 3:

```bash
./scripts/save_map.sh sim_world_toolbox
```

**잘 그리는 요령**: 천천히 움직이고, 제자리 회전은 짧게, 시작 지점으로 한 번 돌아와 루프를 닫으면 지도가 정리됩니다.

## 3. 실제 와플파이로 SLAM (실습실)

모든 기기에서 `scripts/env.sh`의 `ROS_DOMAIN_ID`가 같아야 합니다. 다른 조 로봇과 겹치지 않게 조별로 정하세요.

와플파이 (SSH 접속 후):

```bash
cd ~/uos_ir/slam && git pull
./scripts/robot_bringup.sh
```

Jetson 또는 실습실 PC:

```bash
cd ~/uos_ir/slam && git pull
./scripts/verify_stage0.sh slam_toolbox   # 토픽 확인 → SLAM 실행
ros2 run turtlebot3_teleop teleop_keyboard # 다른 터미널
./scripts/save_map.sh lab_429             # 다른 터미널, 주행 끝나고
```

집에서 쓸 데이터를 녹화할 때는 SLAM 없이 녹화만 합니다:

```bash
./scripts/verify_stage0.sh record
```

> SLAM 실행 중에 녹화하면 bag의 `/tf`에 `map → odom`이 섞여서, 집에서 재생할 때 SLAM 결과와 충돌합니다.

검증이 끝나면 `maps/`는 커밋해서 push하고, `bags/`는 구글 드라이브에 올립니다.

## 4. 녹화 데이터로 다시 돌리기 (집)

```bash
./scripts/replay_bag.sh bags/stage0_20261015_140000 cartographer
```

로봇 없이 같은 데이터로 `slam_toolbox`와 `cartographer`를 비교하거나 파라미터를 튜닝할 수 있습니다.

## 문제 해결

| 증상 | 확인할 것 |
|------|-----------|
| `verify_stage0.sh`에서 `/scan` FAIL | 와플파이 bringup이 켜져 있는지, 같은 Wi-Fi인지, `ROS_DOMAIN_ID`가 같은지 |
| `ros2 topic list`에 아무것도 안 보임 | 실습실 Wi-Fi가 멀티캐스트를 막는 경우 → Fast DDS Discovery Server 사용 검토 |
| 지도가 휘거나 겹침 | 너무 빨리 회전했는지, 오도메트리가 튀는지 (`ros2 topic echo /odom`) |
| LiDAR 데이터가 안 나옴 | `env.sh`의 `LDS_MODEL`이 로봇의 LiDAR(LDS-01/02)와 맞는지 |
| Gazebo가 안 뜨거나 매우 느림 | WSL을 최신으로 업데이트 (`wsl --update`), GPU 드라이버 업데이트 |

## 수업 내용과의 연결

| 수업 | 여기서 볼 수 있는 것 |
|------|------|
| Motion Models | `/odom` — 바퀴 오도메트리, 오래 달리면 누적 오차 |
| Sensor Models | `/scan` — LiDAR 빔 모델 |
| Occupancy Grid Maps | 저장된 `.pgm` (흰색 빈 곳 / 검은색 장애물 / 회색 미확인) |
| Particle Filter | 지도 작성 후 Nav2 AMCL 위치 추정 (다음 단계) |
| Graph-based SLAM | `slam_toolbox` (pose graph + 루프 클로저), `cartographer` |

## 다음 단계

- [ ] 와플파이 ROS 2 버전 확인 → `env.sh` 맞추기
- [ ] 와플파이 LiDAR 모델 (LDS-01 / LDS-02) 확인
- [ ] 조별 `ROS_DOMAIN_ID` 정하기
- [ ] 시뮬레이션 지도 2종 (toolbox / cartographer) 저장
- [ ] 실습실 429호 지도 저장 + rosbag 녹화
- [ ] 저장한 지도로 Nav2 위치 추정·주행 (1단계 준비)

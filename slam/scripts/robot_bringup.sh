#!/usr/bin/env bash
# 와플파이(Raspberry Pi)에서 실행: LiDAR, 오도메트리, 모터 드라이버 시작.
set -eo pipefail
source "$(dirname "$0")/env.sh"
ros2 launch turtlebot3_bringup robot.launch.py

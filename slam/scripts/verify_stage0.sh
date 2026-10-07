#!/usr/bin/env bash
# 실습실에서 (Jetson 또는 실습실 PC): 실제 와플파이로 SLAM 검증 + rosbag 녹화.
# 와플파이에서 robot_bringup.sh 가 먼저 실행 중이어야 한다.
# 사용법: ./verify_stage0.sh [cartographer|slam_toolbox|record]
#   record: SLAM 없이 센서 데이터만 녹화 (집에서 replay_bag.sh 로 쓸 bag 은 이 모드로).
#           SLAM 실행 중 녹화하면 bag 의 /tf 에 map->odom 이 섞여 재생 시 충돌한다.
set -eo pipefail
source "$(dirname "$0")/env.sh"

METHOD="${1:-slam_toolbox}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$SLAM_DIR/logs/$STAMP"
mkdir -p "$LOG_DIR" "$SLAM_DIR/bags"
exec > >(tee "$LOG_DIR/verify.log") 2>&1

echo "== 환경: ROS_DISTRO=$ROS_DISTRO ROS_DOMAIN_ID=$ROS_DOMAIN_ID MODEL=$TURTLEBOT3_MODEL"

echo "== 1. 와플파이 토픽 확인 (10초 대기)"
for t in /scan /odom /tf; do
  if timeout 10 ros2 topic echo --once "$t" > /dev/null 2>&1; then
    echo "  [OK]   $t"
  else
    echo "  [FAIL] $t  → 와플파이 bringup, Wi-Fi, ROS_DOMAIN_ID, 멀티캐스트 확인"
    FAILED=1
  fi
done
[ -z "${FAILED:-}" ] || exit 1

echo "== 2. 토픽 주기"
timeout 5 ros2 topic hz /scan || true

echo "== 3. rosbag 녹화 시작 (집에서 재생용)"
ros2 bag record -s mcap -o "$SLAM_DIR/bags/stage0_$STAMP" /scan /odom /tf /tf_static /imu &
BAG_PID=$!
trap 'kill -INT $BAG_PID 2>/dev/null; wait $BAG_PID 2>/dev/null' EXIT

echo "== 4. $METHOD 실행. 다른 터미널에서 teleop 으로 주행 (SLAM 모드면 끝나기 전에 save_map.sh lab_$STAMP)"
case "$METHOD" in
  cartographer) ros2 launch turtlebot3_cartographer cartographer.launch.py ;;
  slam_toolbox) ros2 launch slam_toolbox online_async_launch.py ;;
  record)       echo "녹화 중. teleop 으로 주행 후 Ctrl+C"; wait $BAG_PID ;;
  *)            echo "알 수 없는 방식: $METHOD" >&2; exit 1 ;;
esac

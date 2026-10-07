#!/usr/bin/env bash
# 집에서: 실습실에서 녹화한 rosbag 으로 SLAM 다시 돌리기 (로봇 없이 파라미터 튜닝).
# bag 은 verify_stage0.sh record 모드로 녹화한 것을 쓴다.
# 사용법: ./replay_bag.sh <bag 폴더> [cartographer|slam_toolbox]
set -eo pipefail
source "$(dirname "$0")/env.sh"

BAG="${1:?bag 폴더를 지정하세요 (예: ../bags/stage0_20261015_140000)}"
METHOD="${2:-slam_toolbox}"

case "$METHOD" in
  cartographer) ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=True & ;;
  slam_toolbox) ros2 launch slam_toolbox online_async_launch.py use_sim_time:=True & ;;
  *)            echo "알 수 없는 방식: $METHOD" >&2; exit 1 ;;
esac
SLAM_PID=$!
trap 'kill $SLAM_PID 2>/dev/null' EXIT
sleep 5
ros2 bag play "$BAG" --clock
echo "재생 끝. 종료 전에 save_map.sh 로 지도를 저장하세요. (Ctrl+C 로 종료)"
wait $SLAM_PID

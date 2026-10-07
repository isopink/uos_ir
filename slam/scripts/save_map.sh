#!/usr/bin/env bash
# SLAM 실행 중에 다른 터미널에서 지도 저장. 결과: maps/<이름>.pgm, maps/<이름>.yaml
# 사용법: ./save_map.sh [이름]
set -eo pipefail
source "$(dirname "$0")/env.sh"

NAME="${1:-map_$(date +%Y%m%d_%H%M%S)}"
ros2 run nav2_map_server map_saver_cli -f "$SLAM_DIR/maps/$NAME"
echo "저장됨: $SLAM_DIR/maps/$NAME.{pgm,yaml}"

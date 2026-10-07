# 공통 환경 변수. 다른 스크립트에서 source 한다.
# 와플파이와 Jetson/노트북이 같은 값을 써야 서로 토픽이 보인다.
export ROS_DISTRO="${ROS_DISTRO:-humble}"
export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-waffle_pi}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-30}"   # 조마다 다르게 (다른 조 로봇과 섞이지 않게)
export LDS_MODEL="${LDS_MODEL:-LDS-02}"       # 와플파이 LiDAR 모델 (LDS-01 / LDS-02, 로봇 스티커 확인)

source "/opt/ros/${ROS_DISTRO}/setup.bash"
SLAM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export SLAM_DIR

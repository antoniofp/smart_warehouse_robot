#!/bin/bash

# Script to save the SLAM map easily

if [ -z "$1" ]; then
  echo -e "\033[1;33m[WARNING] No map name provided.\033[0m"
  echo "Usage: ./save_map.sh <map_name>"
  echo "Example: ./save_map.sh my_new_map"
  exit 1
fi

echo -e "\033[1;32m[INFO] Saving map as $1...\033[0m"

# Source ROS 2 base environment
source /opt/ros/foxy/setup.bash

# Ensure the maps directory exists
mkdir -p src/r2_nav/maps

# Run the nav2_map_server command to save the map
ros2 run nav2_map_server map_saver_cli -f "src/r2_nav/maps/$1" --ros-args -p map_subscribe_transient_local:=true

echo -e "\033[1;32m[SUCCESS] Map successfully saved at src/r2_nav/maps/$1.yaml\033[0m"

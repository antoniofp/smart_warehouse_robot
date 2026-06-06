#!/bin/bash

# Consolidate all startup commands for the Smart Warehouse Robot SLAM Localization & Navigation
# Author: Antigravity AI

# 1. Source all ROS 2 environments in order
source /opt/ros/foxy/setup.bash
source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash
source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
source /root/smart_warehouse_robot/install/setup.bash

# 2. Critical: Use CycloneDDS for SLAM stability on Jetson Nano
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=32
export ROBOT_TYPE=r2
export RPLIDAR_TYPE=a1

echo "----------------------------------------------------"
echo "Cleaning up previous ROS 2 processes..."
# Silently call the dedicated panic button script from the original directory
/root/smart_warehouse_robot/kill_all_ros.sh > /dev/null 2>&1 || true
sleep 2

echo "Initializing Smart Warehouse Robot Localization & Navigation System (SLAM)..."
echo "----------------------------------------------------"

# Create log directory if it does not exist
mkdir -p /root/smart_warehouse_robot/log

# 3. Start ROSboard (for visualization and web control)
echo "[1/5] Starting ROSboard..."
cd /root/rosboard && ./run > /dev/null 2>&1 &
ROSBOARD_PID=$!

# 4. Start Foxglove Bridge (for modern web-based telemetry)
echo "[2/5] Starting Foxglove Bridge..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml > /dev/null 2>&1 &
FOXGLOVE_PID=$!

# 5. Start Hardware Bringup (Laser + Base)
echo "[3/5] Starting Hardware Bringup (Laser + Base)..."
ros2 launch yahboomcar_nav laser_bringup_launch.py steering_offset:=0.0 linear_scale_y:=0.78 > /root/smart_warehouse_robot/log/bringup.log 2>&1 &
BRINGUP_PID=$!

# 6. Start RGB Camera Feed
echo "[4/5] Starting RGB Camera Node..."
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv" > /dev/null 2>&1 &
CAMERA_PID=$!

# 7. Start SLAM Toolbox (Localization Mode) + Nav2 Navigation
echo "[5/5] Starting SLAM Localization & Nav2 Navigation..."
ros2 launch r2_nav slam_navigation_launch.py \
  params_file:=/root/smart_warehouse_robot/src/r2_nav/config/nav2_params.yaml \
  default_bt_xml_filename:=/root/smart_warehouse_robot/src/r2_nav/behavior_trees/minimal_bt.xml \
  > /root/smart_warehouse_robot/log/slam_nav.log 2>&1 &
SLAM_PID=$!

echo "----------------------------------------------------"
echo "All SLAM localization and navigation systems are running."
echo "Access ROSboard at: http://localhost:8888"
echo "Access Foxglove via: ws://localhost:9090 (or robot IP)"
echo "Press Ctrl+C to shut down all nodes safely."
echo "----------------------------------------------------"

# Handle safe shutdown on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down all processes..."
    # Kill background processes cleanly
    kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $SLAM_PID 2>/dev/null

    # Run the ultimate panic button in the original directory
    /root/smart_warehouse_robot/kill_all_ros.sh > /dev/null 2>&1 || true

    echo "Done. All topics and nodes have been cleared."
    exit
}

trap cleanup INT

# Keep script active to monitor background tasks
wait

#!/bin/bash

# Consolidate all startup commands for the Smart Warehouse Robot Navigation
# Author: Antigravity AI

# 1. Source all ROS 2 environments in order
source /opt/ros/foxy/setup.bash
source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash
source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
source /root/smart_warehouse_robot/install/setup.bash

# 2. Critical: Use CycloneDDS for SLAM/Nav stability on Jetson Nano
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "----------------------------------------------------"
echo "Cleaning up any previous ROS 2 processes..."
pkill -f "ros2" || true
pkill -f "Ackman_driver_R2" || true
pkill -f "yahboom_joy_R2" || true
pkill -f "joint_state_publisher" || true
pkill -f "rosboard" || true
ros2 daemon stop 2>/dev/null || true
sleep 1

echo "Initializing Smart Warehouse Robot Navigation System (AMCL + TEB)..."
echo "----------------------------------------------------"

# 3. Start ROSboard (for visualization and web control)
echo "[1/5] Starting ROSboard..."
cd /root/rosboard && ./run > /dev/null 2>&1 &
ROSBOARD_PID=$!

# 4. Start Foxglove Bridge (for modern web-based telemetry)
echo "[2/5] Starting Foxglove Bridge..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml > /dev/null 2>&1 &
FOXGLOVE_PID=$!

# 5. Start Hardware Bringup (Chassis + Lidar)
echo "[3/5] Starting Hardware Bringup (Laser + Base)..."
ros2 launch yahboomcar_nav laser_bringup_launch.py > /dev/null 2>&1 &
BRINGUP_PID=$!

# 6. Start RGB Camera Feed
echo "[4/5] Starting RGB Camera Node..."
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv" > /dev/null 2>&1 &
CAMERA_PID=$!

# 7. Start Nav2 Bringup (with AMCL localization and custom TEB controller)
echo "[5/5] Starting Nav2 Navigation (AMCL + TEB)..."
ros2 launch r2_nav bringup_launch.py params_file:=/root/smart_warehouse_robot/src/r2_nav/config/nav2_params.yaml default_bt_xml_filename:=/root/smart_warehouse_robot/minimal_bt.xml > /dev/null 2>&1 &
NAV_PID=$!

echo "----------------------------------------------------"
echo "All navigation systems are running."
echo "Access ROSboard at: http://localhost:8888"
echo "Access Foxglove via: ws://localhost:9090 (or robot IP)"
echo "Press Ctrl+C to shut down all nodes safely."
echo "----------------------------------------------------"

# Handle safe shutdown on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down all processes..."
    kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $NAV_PID 2>/dev/null

    pkill -f "ros2"
    pkill -f "rosbridge"
    pkill -f "Ackman_driver_R2"
    pkill -f "yahboom_joy_R2"
    pkill -f "joint_state_publisher"
    pkill -f "robot_state_publisher"
    pkill -f "slam_toolbox"
    pkill -f "usb_cam_node_exe"
    pkill -f "rosboard"
    pkill -f "sllidar_node"
    pkill -f "lifecycle_manager"

    ros2 daemon stop 2>/dev/null
    echo "Done. All topics and nodes have been cleared."
    exit
}

trap cleanup INT

wait

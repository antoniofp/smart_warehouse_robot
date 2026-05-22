#!/bin/bash

# Consolidate all startup commands for the Smart Warehouse Robot SLAM Testing
# Author: Gemini CLI

# 1. Source all ROS 2 environments in order
source /opt/ros/foxy/setup.bash
source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash
source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
source /root/smart_warehouse_robot/install/setup.bash

# 2. Critical: Use CycloneDDS for SLAM stability on Jetson Nano
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "----------------------------------------------------"
echo "Initializing Smart Warehouse Robot Mapping System..."
echo "----------------------------------------------------"

# 3. Start ROSboard (for visualization and web control)
echo "[1/4] Starting ROSboard..."
cd /root/rosboard && ./run > /dev/null 2>&1 &
ROSBOARD_PID=$!

# 4. Start Hardware Bringup (Chassis + Lidar)
echo "[2/4] Starting Hardware Bringup (Laser + Base)..."
ros2 launch yahboomcar_nav laser_bringup_launch.py > /dev/null 2>&1 &
BRINGUP_PID=$!

# 5. Start RGB Camera Feed
echo "[3/4] Starting RGB Camera Node..."
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv" > /dev/null 2>&1 &
CAMERA_PID=$!

# 6. Start SLAM Toolbox (Async Mapping)
echo "[4/4] Starting SLAM Toolbox (Online Async)..."
ros2 launch slam_toolbox online_async_launch.py > /dev/null 2>&1 &
SLAM_PID=$!

echo "----------------------------------------------------"
echo "All systems are running."
echo "Access ROSboard at: http://localhost:8888 (or robot IP)"
echo "Press Ctrl+C to shut down all nodes safely."
echo "----------------------------------------------------"

# Handle safe shutdown on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down all processes..."
    kill $ROSBOARD_PID $BRINGUP_PID $CAMERA_PID $SLAM_PID 2>/dev/null
    echo "Done."
    exit
}

trap cleanup INT

# Keep the script running to manage background processes
wait

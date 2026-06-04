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
export ROS_DOMAIN_ID=32
export ROBOT_TYPE=r2
export RPLIDAR_TYPE=a1
export CAMERA_TYPE=astraplus

echo "----------------------------------------------------"
echo "Cleaning up previous ROS 2 processes..."
# Silently call the dedicated panic button script to avoid duplicate output
/root/smart_warehouse_robot/kill_all_ros.sh > /dev/null 2>&1 || true
sleep 2

echo "Initializing Smart Warehouse Robot Navigation System (AMCL + Pure Pursuit)..."
echo "----------------------------------------------------"

# 3. Start ROSboard (Disabled to save CPU)
# echo "[1/5] Starting ROSboard..."
# cd /root/rosboard && ./run > /dev/null 2>&1 &
ROSBOARD_PID=

# 4. Start Foxglove Bridge (for modern web-based telemetry)
echo "[2/5] Starting Foxglove Bridge..."
ros2 launch rosbridge_server rosbridge_websocket_launch.xml > /dev/null 2>&1 &
FOXGLOVE_PID=$!

# 5. Start Hardware Bringup (Laser + Base)
echo "[3/5] Starting Hardware Bringup (Laser + Base)..."
ros2 launch yahboomcar_nav laser_bringup_launch.py > /dev/null 2>&1 &
BRINGUP_PID=$!

# 6. Start RGB Camera Feed (Limited to 5 FPS to reduce CPU usage)
echo "[4/5] Starting RGB Camera Node..."
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv" -p framerate:=5.0 > /dev/null 2>&1 &
CAMERA_PID=$!

# 7. Start Nav2 Bringup (with AMCL localization and Regulated Pure Pursuit controller)
# Redirecting output to a dedicated log file for easy real-time debugging
echo "[5/5] Starting Nav2 Navigation (AMCL + Pure Pursuit)..."
mkdir -p /root/smart_warehouse_robot/log
ros2 launch r2_nav bringup_launch.py params_file:=/root/smart_warehouse_robot/src/r2_nav/config/nav2_params.yaml default_bt_xml_filename:=/root/smart_warehouse_robot/src/r2_nav/behavior_trees/minimal_bt.xml > /root/smart_warehouse_robot/log/nav2.log 2>&1 &
NAV_PID=$!

# 7.5. Start real-time Pose Logger
echo "Starting real-time Pose Logger..."
python3 /root/smart_warehouse_robot/pose_logger.py > /dev/null 2>&1 &
POSE_LOGGER_PID=$!


# =====================================================================
#                      INITIAL POSE CONFIGURATION
# You can pass coordinates as arguments: ./start_navigation.sh [X] [Y] [YAW_DEG]
# Example: ./start_navigation.sh 1.5 -0.8 90
# If no arguments are passed, it defaults to X=0.0, Y=0.0, YAW=0.0 degrees.
# =====================================================================
INITIAL_X="${1:-0.0}"
INITIAL_Y="${2:--0.9}"
INITIAL_YAW_DEG="${3:-0.0}"

# Convert YAW from degrees to Quaternion Z and W using python3 automatically
INITIAL_Z_ORIENT=$(python3 -c "import math; print(math.sin(math.radians($INITIAL_YAW_DEG) / 2.0))")
INITIAL_W_ORIENT=$(python3 -c "import math; print(math.cos(math.radians($INITIAL_YAW_DEG) / 2.0))")
# =====================================================================


# 8. Automatically publish initial pose once AMCL is active
(
    echo "Waiting for AMCL to initialize before publishing initial pose..."
    # Wait for the amcl node to appear in the active node list
    for i in {1..30}; do
        if ros2 node list 2>/dev/null | grep -q "/amcl"; then
            echo "AMCL node detected! Sourcing environment to publish..."
            source /opt/ros/foxy/setup.bash
            source /root/smart_warehouse_robot/install/setup.bash
            export ROS_DOMAIN_ID=32
export ROBOT_TYPE=r2
export RPLIDAR_TYPE=a1
export CAMERA_TYPE=astraplus
            export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

            echo "Publishing initial pose (x: $INITIAL_X, y: $INITIAL_Y, yaw: $INITIAL_YAW_DEG deg)..."
            ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped "{header: {stamp: {sec: 0, nanosec: 0}, frame_id: 'map'}, pose: {pose: {position: {x: $INITIAL_X, y: $INITIAL_Y, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: $INITIAL_Z_ORIENT, w: $INITIAL_W_ORIENT}}, covariance: [0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.06853891945200942]}}" > /dev/null 2>&1

            echo ""
            echo "=========================================================="
            echo " SUCCESS: Initial pose published!                         "
            echo "          X: $INITIAL_X, Y: $INITIAL_Y, YAW: $INITIAL_YAW_DEG deg"
            echo "          Navigation is fully initialized and ready!      "
            echo "=========================================================="
            echo ""
            break
        fi
        sleep 1
    done
) &
AUTO_POSE_PID=$!

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
    # Kill background processes cleanly
    kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $NAV_PID $AUTO_POSE_PID $POSE_LOGGER_PID 2>/dev/null

    # Run the ultimate panic button to clean ROS 2 and drivers
    /root/smart_warehouse_robot/kill_all_ros.sh > /dev/null 2>&1 || true

    echo "Done. All topics and nodes have been cleared."
    exit
}

trap cleanup INT

# Keep script active to monitor background tasks
wait

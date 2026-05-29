#!/bin/bash

# Utility script to send a navigation goal to the robot from the command line
# Author: Antigravity AI

# 1. Source all ROS 2 environments in order (Only if not already sourced to speed up execution)
if ! command -v ros2 &> /dev/null; then
    source /opt/ros/foxy/setup.bash
    source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash
    source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
    source /root/smart_warehouse_robot/install/setup.bash
fi

# 2. Critical: Use CycloneDDS and matching Domain ID
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=32

# =====================================================================
#                      GOAL POSE CONFIGURATION
# You can pass coordinates as arguments: ./send_goal.sh [X] [Y] [YAW_DEG]
# Example: ./send_goal.sh 1.5 0.0 0
# If no arguments are passed, it defaults to X=0.0, Y=0.0, YAW=0.0 degrees.
# =====================================================================
GOAL_X="${1:-0.0}"
GOAL_Y="${2:-0.0}"
GOAL_YAW_DEG="${3:-0.0}"

# Convert YAW from degrees to Quaternion Z and W using python3 automatically
GOAL_Z_ORIENT=$(python3 -c "import math; print(math.sin(math.radians($GOAL_YAW_DEG) / 2.0))")
GOAL_W_ORIENT=$(python3 -c "import math; print(math.cos(math.radians($GOAL_YAW_DEG) / 2.0))")
# =====================================================================

echo "----------------------------------------------------"
echo "Sending navigation goal to robot..."
echo "Target X  : $GOAL_X meters"
echo "Target Y  : $GOAL_Y meters"
echo "Target Yaw: $GOAL_YAW_DEG degrees"
echo "----------------------------------------------------"

# Publish the goal pose once to /goal_pose topic
ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped "{header: {stamp: {sec: 0, nanosec: 0}, frame_id: 'map'}, pose: {position: {x: $GOAL_X, y: $GOAL_Y, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: $GOAL_Z_ORIENT, w: $GOAL_W_ORIENT}}}" > /dev/null 2>&1

echo "SUCCESS: Navigation goal successfully sent!"
echo "----------------------------------------------------"
echo "Waiting for Nav2 feedback (3 seconds)..."
echo "----------------------------------------------------"
sleep 3

# Print the last 15 lines of Nav2 log for instant diagnosis
if [ -f /root/smart_warehouse_robot/log/nav2.log ]; then
    tail -n 15 /root/smart_warehouse_robot/log/nav2.log
else
    echo "No Nav2 log file found at /root/smart_warehouse_robot/log/nav2.log"
fi
echo "----------------------------------------------------"

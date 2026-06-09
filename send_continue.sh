#!/bin/bash

# Script to send the 'continue' confirmation message to the robot's loading zone rule
# Author: Antigravity AI

# Source the ROS 2 environment
source /opt/ros/foxy/setup.bash
source /root/smart_warehouse_robot/install/setup.bash

# Configure network and domain parameters
export ROS_DOMAIN_ID=32
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

echo "[INFO] Sending 'continue' confirmation to /pc_confirmation..."
ros2 topic pub --once /pc_confirmation std_msgs/msg/String "{data: 'continue'}"
echo "[INFO] Confirmation sent successfully."

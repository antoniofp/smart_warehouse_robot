#!/bin/bash
echo "Stopping all ROS 2 nodes and related processes..."

# Kill ROS 2 nodes
pkill -f "ros2"
pkill -f "Ackman_driver_R2"
pkill -f "yahboom_joy_R2"
pkill -f "joint_state_publisher"
pkill -f "robot_state_publisher"
pkill -f "slam_toolbox"
pkill -f "usb_cam_node_exe"
pkill -f "rosboard"
pkill -f "sllidar_node"

# Kill any remaining python processes related to ROS
pkill -f "python3 /opt/ros/foxy"
pkill -f "python3 /root/yahboomcar_ros2_ws"

# Cleanup daemon
ros2 daemon stop 2>/dev/null

echo "Cleanup complete."

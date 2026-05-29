#!/bin/bash
# Stop ROS 2 navigation, drivers, and visualization nodes
echo "Stopping ROS 2 and Navigation nodes..."

# Kill specific ROS 2, Nav2, and Yahboom driver processes
pkill -f "ros2|amcl|map_server|planner_server|controller_server|bt_navigator|lifecycle_manager|recoveries_server|robot_state_publisher|joint_state_publisher|slam_toolbox|usb_cam_node_exe|rosboard|sllidar_node|Ackman_driver_R2|yahboom_joy_R2|rosbridge" || true

# Stop the ROS 2 daemon cleanly
ros2 daemon stop 2>/dev/null || true

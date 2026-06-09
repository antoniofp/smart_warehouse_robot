#!/bin/bash

# Unified script to start SLAM navigation and launch the mission
# Author: Antigravity AI

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Handle clean shutdown on Ctrl+C or script termination
cleanup() {
    echo ""
    echo "[WARNING] Mission interrupted. Cleaning up ROS 2 processes..."
    kill $NAV_PID 2>/dev/null
    $DIR/kill_all_ros.sh > /dev/null 2>&1 || true
    exit 1
}
trap cleanup INT TERM

echo "===================================================="
echo " Starting Smart Warehouse Robot Mission Flow"
echo "===================================================="

# Kill any orphaned mission_vision.py processes to free up UDP port 5005
pkill -f mission_vision.py 2>/dev/null || true

# Create log directory if it doesn't exist
mkdir -p $DIR/log

# 1. Start SLAM Navigation in the background
echo "[1/2] Launching SLAM Navigation (in background)..."
$DIR/start_slam_navigation.sh > $DIR/log/slam_nav_startup.log 2>&1 &
NAV_PID=$!

# Wait for Navigation stack to fully initialize (30 seconds for stability)
echo "[INFO] Waiting 30 seconds for Navigation stack to initialize..."
sleep 30

# 2. Launch Mission Vision node in the foreground
echo "[2/2] Starting Mission Vision Controller..."
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><NetworkInterfaceAddress>wlan0</NetworkInterfaceAddress></General></Domain></CycloneDDS>'
export CYCLONEDDS_LOG_LEVEL=error
python3 -u $DIR/scripts/mission_vision.py

echo "[INFO] Mission finished. Cleaning up..."
# Clean shutdown of SLAM navigation
kill $NAV_PID 2>/dev/null
$DIR/kill_all_ros.sh > /dev/null 2>&1 || true

echo "===================================================="
echo " Mission execution completed."
echo "===================================================="

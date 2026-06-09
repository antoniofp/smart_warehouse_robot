with open('/root/smart_warehouse_robot/start_navigation.sh', 'r') as f:
    content = f.read()

old_nav_pid = "NAV_PID=$!"
new_nav_pid = """NAV_PID=$!

# Start real-time Pose Logger
echo "Starting real-time Pose Logger..."
python3 /root/smart_warehouse_robot/pose_logger.py > /dev/null 2>&1 &
POSE_LOGGER_PID=$!"""

if old_nav_pid in content:
    content = content.replace(old_nav_pid, new_nav_pid)

old_kill = "kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $NAV_PID $AUTO_POSE_PID"
new_kill = "kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $NAV_PID $AUTO_POSE_PID $POSE_LOGGER_PID"

if old_kill in content:
    content = content.replace(old_kill, new_kill)

with open('/root/smart_warehouse_robot/start_navigation.sh', 'w') as f:
    f.write(content)

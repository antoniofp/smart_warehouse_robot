import os

path = '/root/smart_warehouse_robot/start_navigation.sh'
with open(path, 'r') as f:
    content = f.read()

# 1. Add logger start after pose_logger.py
old_logger = """# 7.5. Start real-time Pose Logger
echo "Starting real-time Pose Logger..."
python3 /root/smart_warehouse_robot/pose_logger.py > /dev/null 2>&1 &
POSE_LOGGER_PID=$!"""

new_logger = """# 7.5. Start real-time Pose Logger
echo "Starting real-time Pose Logger..."
python3 /root/smart_warehouse_robot/pose_logger.py > /dev/null 2>&1 &
POSE_LOGGER_PID=$!

# 7.6. Start real-time Odom-IMU Logger
echo "Starting real-time Odom-IMU Logger..."
python3 /root/smart_warehouse_robot/odom_imu_logger.py > /root/smart_warehouse_robot/log/odom_imu.log 2>&1 &
ODOM_IMU_LOGGER_PID=$!"""

if old_logger in content:
    if "ODOM_IMU_LOGGER_PID" not in content:
        content = content.replace(old_logger, new_logger)
        print("Logger start block added successfully.")
    else:
        print("Logger start block already exists.")
else:
    print("Could not find the pose logger start block!")

# 2. Add logger cleanup inside trap/cleanup
old_cleanup = "kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $NAV_PID $AUTO_POSE_PID $POSE_LOGGER_PID 2>/dev/null"
new_cleanup = "kill $ROSBOARD_PID $FOXGLOVE_PID $BRINGUP_PID $CAMERA_PID $NAV_PID $AUTO_POSE_PID $POSE_LOGGER_PID $ODOM_IMU_LOGGER_PID 2>/dev/null"

if old_cleanup in content:
    content = content.replace(old_cleanup, new_cleanup)
    print("Logger cleanup command updated successfully.")
else:
    # Try finding it without space at the end or slightly different format
    if "kill" in content and "POSE_LOGGER_PID" in content and "ODOM_IMU_LOGGER_PID" not in content:
        # Let's do a more robust replacement
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            if "kill" in line and "POSE_LOGGER_PID" in line:
                lines[idx] = line.replace("POSE_LOGGER_PID", "POSE_LOGGER_PID $ODOM_IMU_LOGGER_PID")
                print(f"Robust replacement on line: {line}")
        content = "\\n".join(lines)
    else:
        print("Cleanup command already updated or not found.")

with open(path, 'w') as f:
    f.write(content)

print("Patching complete.")

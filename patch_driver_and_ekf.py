import os
import subprocess

# 1. Patch Ackman_driver_R2.py (to invert gyro Z)
driver_path = '/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_bringup/yahboomcar_bringup/Ackman_driver_R2.py'

if os.path.exists(driver_path):
    with open(driver_path, 'r') as f:
        content = f.read()
    
    old_line = 'imu.angular_velocity.z = gz*1.0'
    new_line = 'imu.angular_velocity.z = -gz*1.0'
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("Driver successfully patched (inverted gyro Z).")
        with open(driver_path, 'w') as f:
            f.write(content)
    elif new_line in content:
        print("Driver already patched (gyro Z already inverted).")
    else:
        print("Error: Could not find gyro Z assignment in driver script!")
else:
    print(f"Error: Driver path not found: {driver_path}")

# 2. Patch EKF yaml
ekf_src_path = '/root/yahboomcar_ros2_ws/software/library_ws/src/robot_localization/params/ekf_x1_x3.yaml'
ekf_inst_path = '/root/yahboomcar_ros2_ws/software/library_ws/install/robot_localization/share/robot_localization/params/ekf_x1_x3.yaml'

def patch_ekf_file(path):
    if not os.path.exists(path):
        print(f"Error: EKF path not found: {path}")
        return False
        
    with open(path, 'r') as f:
        lines = f.readlines()
        
    odom0_found = False
    imu0_found = False
    modified = False
    
    for i, line in enumerate(lines):
        if 'odom0_config:' in line:
            # We want to change odom0_config to:
            # odom0_config: [true, true, false, false, false, false, true, true, false, false, false, false, false, false, false]
            # Replace the next 3 lines containing configuration values
            lines[i]   = "        odom0_config: [true, true, false,\n"
            lines[i+1] = "                       false, false, false,\n"
            lines[i+2] = "                       true, true, false,\n"
            lines[i+3] = "                       false, false, false,\n"
            lines[i+4] = "                       false, false, false]\n"
            odom0_found = True
            modified = True
            print(f"Patched odom0_config in {path}")
            
        elif 'imu0_config:' in line:
            # We want to change imu0_config to:
            # imu0_config: [false, false, false, false, false, false, false, false, false, false, false, true, false, false, false]
            lines[i]   = "        imu0_config: [false, false, false,\n"
            lines[i+1] = "                      false, false, false ,\n"
            lines[i+2] = "                      false, false, false,\n"
            lines[i+3] = "                      false, false, true,\n"
            lines[i+4] = "                      false, false, false]\n"
            imu0_found = True
            modified = True
            print(f"Patched imu0_config in {path}")
            
    if modified:
        with open(path, 'w') as f:
            f.writelines(lines)
        return True
    return False

patch_ekf_file(ekf_src_path)
patch_ekf_file(ekf_inst_path)

# 3. Rebuild the workspace inside the container
print("Rebuilding workspace using colcon build...")
try:
    # Run colcon build for yahboomcar_bringup package
    res = subprocess.run(
        ["/bin/bash", "-c", "source /opt/ros/foxy/setup.bash && cd /root/yahboomcar_ros2_ws/yahboomcar_ws && colcon build --packages-select yahboomcar_bringup"],
        capture_output=True, text=True, check=True
    )
    print("Colcon build output:")
    print(res.stdout)
except subprocess.CalledProcessError as e:
    print("Colcon build failed!")
    print(e.stderr)

import os
import subprocess

# 1. Patch Ackman_driver_R2.py (to ensure correct accelerometer Z coordinate frame)
driver_path = '/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_bringup/yahboomcar_bringup/Ackman_driver_R2.py'

if os.path.exists(driver_path):
    with open(driver_path, 'r') as f:
        content = f.read()
    
    old_line = 'imu.linear_acceleration.z = az*1.0'
    new_line = 'imu.linear_acceleration.z = -az*1.0'
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        print("Driver successfully patched (inverted accelerometer Z for correct gravity vector orientation).")
        with open(driver_path, 'w') as f:
            f.write(content)
    elif new_line in content:
        print("Driver already patched (accelerometer Z is already inverted).")
    else:
        print("Warning: Could not find accelerometer Z adjustment in driver script.")
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
    process_noise_found = False
    modified = False
    
    for i, line in enumerate(lines):
        if 'odom0_config:' in line:
            # Fuse position (x, y), orientation (yaw), velocities (vx, vy), and yaw rate (vyaw) from wheel odometry.
            lines[i]   = "        odom0_config: [true, true, false,\n"
            lines[i+1] = "                       false, false, true,\n"
            lines[i+2] = "                       true, true, false,\n"
            lines[i+3] = "                       false, false, true,\n"
            lines[i+4] = "                       false, false, false]\n"
            odom0_found = True
            modified = True
            print(f"Patched odom0_config in {path}")
            
        elif 'imu0_config:' in line:
            # Fuse orientation (yaw) and yaw rate (vyaw) from IMU
            lines[i]   = "        imu0_config: [false, false, false,\n"
            lines[i+1] = "                      false, false, true ,\n"
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

# 2.5. Patch imu_filter_param.yaml (to ensure use_mag is false)
imu_filter_src = '/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_bringup/param/imu_filter_param.yaml'
imu_filter_inst = '/root/yahboomcar_ros2_ws/yahboomcar_ws/install/yahboomcar_bringup/share/yahboomcar_bringup/param/imu_filter_param.yaml'

def patch_imu_filter(path):
    if not os.path.exists(path):
        print(f"Warning: IMU filter path not found: {path}")
        return False
        
    with open(path, 'r') as f:
        content = f.read()
        
    if 'use_mag: true' in content:
        content = content.replace('use_mag: true', 'use_mag: false')
        with open(path, 'w') as f:
            f.write(content)
        print(f"Patched use_mag to false in {path}")
        return True
    elif 'use_mag: false' in content:
        print(f"IMU filter already has use_mag set to false in {path}")
        return True
    else:
        print(f"Warning: use_mag parameter not found in {path}")
        return False

patch_imu_filter(imu_filter_src)
patch_imu_filter(imu_filter_inst)

# 3. Rebuild the workspace inside the container
print("Rebuilding workspace using colcon build...")
try:
    # Run colcon build for yahboomcar_bringup package
    res1 = subprocess.run(
        ["/bin/bash", "-c", "source /opt/ros/foxy/setup.bash && cd /root/yahboomcar_ros2_ws/yahboomcar_ws && colcon build --packages-select yahboomcar_bringup"],
        capture_output=True, text=True, check=True
    )
    print("yahboomcar_bringup build output:")
    print(res1.stdout)
    
    # Run colcon build for robot_localization package
    res2 = subprocess.run(
        ["/bin/bash", "-c", "source /opt/ros/foxy/setup.bash && cd /root/yahboomcar_ros2_ws/software/library_ws && colcon build --packages-select robot_localization"],
        capture_output=True, text=True, check=True
    )
    print("robot_localization build output:")
    print(res2.stdout)
except subprocess.CalledProcessError as e:
    print("Colcon build failed!")
    print(e.stderr)

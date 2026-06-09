import os
import subprocess

# 1. Revert Ackman_driver_R2.py to original state
driver_path = '/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_bringup/yahboomcar_bringup/Ackman_driver_R2.py'
if os.path.exists(driver_path):
    with open(driver_path, 'r') as f:
        content = f.read()
    
    new_line = 'imu.angular_velocity.z = -gz*1.0'
    old_line = 'imu.angular_velocity.z = gz*1.0'
    
    if new_line in content:
        content = content.replace(new_line, old_line)
        print("Driver reverted back to manufacturer gyro state.")
        with open(driver_path, 'w') as f:
            f.write(content)

# 2. Revert EKF yaml parameters
ekf_src_path = '/root/yahboomcar_ros2_ws/software/library_ws/src/robot_localization/params/ekf_x1_x3.yaml'
ekf_inst_path = '/root/yahboomcar_ros2_ws/software/library_ws/install/robot_localization/share/robot_localization/params/ekf_x1_x3.yaml'

def revert_ekf_file(path):
    if not os.path.exists(path):
        return
        
    with open(path, 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if 'odom0_config:' in line:
            # Revert to manufacturer odom config (fusing absolute yaw and velocity)
            lines[i]   = "        odom0_config: [true, true, false,\n"
            lines[i+1] = "                       false, false, true,\n"
            lines[i+2] = "                       true, true, false,\n"
            lines[i+3] = "                       false, false, true,\n"
            lines[i+4] = "                       false, false, false]\n"
            
        elif 'imu0_config:' in line:
            # Revert to all false for imu0_config
            lines[i]   = "        imu0_config: [false, false, false,\n"
            lines[i+1] = "                      false, false, false ,\n"
            lines[i+2] = "                      false, false, false,\n"
            lines[i+3] = "                      false, false, false,\n"
            lines[i+4] = "                      false, false, false]\n"
            
    with open(path, 'w') as f:
        f.writelines(lines)
    print(f"Reverted EKF parameters in {path}")

revert_ekf_file(ekf_src_path)
revert_ekf_file(ekf_inst_path)

# 3. Patch launch file to include linear_scale_y = 0.83
launch_path = '/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_bringup/launch/yahboomcar_bringup_R2_launch.py'
if os.path.exists(launch_path):
    with open(launch_path, 'r') as f:
        content = f.read()
        
    old_base_node = """    base_node = Node(
        package='yahboomcar_base_node',
        executable='base_node_R2',
        # 当使用ekf融合时，该tf有ekf发布
        parameters=[{'pub_odom_tf': LaunchConfiguration('pub_odom_tf')}]
    )"""
    
    new_base_node = """    base_node = Node(
        package='yahboomcar_base_node',
        executable='base_node_R2',
        # 当使用ekf融合时，该tf有ekf发布
        parameters=[{'pub_odom_tf': LaunchConfiguration('pub_odom_tf'),
                     'linear_scale_y': 0.83}]
    )"""
    
    if old_base_node in content:
        content = content.replace(old_base_node, new_base_node)
        print("Patched launch file with steering scale factor (0.83).")
        with open(launch_path, 'w') as f:
            f.write(content)
    elif new_base_node in content:
        print("Launch file already contains steering scale factor.")
    else:
        print("Error: Could not locate base_node configuration in launch file!")

# 4. Rebuild workspace using colcon build
print("Rebuilding workspace using colcon build...")
try:
    res = subprocess.run(
        ["/bin/bash", "-c", "source /opt/ros/foxy/setup.bash && cd /root/yahboomcar_ros2_ws/yahboomcar_ws && colcon build --packages-select yahboomcar_bringup"],
        capture_output=True, text=True, check=True
    )
    print("Colcon build output:")
    print(res.stdout)
except subprocess.CalledProcessError as e:
    print("Colcon build failed!")
    print(e.stderr)

# EKF Parameters and LiDAR Calibration Backup Info

This document tracks the calibration changes made to the EKF (`robot_localization`) node and static LiDAR transforms to prevent LiDAR scan rotation/skew drift during turns on the Ackermann R2 robot.

## Backup File Locations (on Jetson)
The original configuration files were backed up on the Jetson Nano filesystem at:
1. **Source EKF YAML:** `/root/yahboomcar_ros2_ws/software/library_ws/src/robot_localization/params/ekf_x1_x3.yaml.bak`
2. **Installed EKF YAML:** `/root/yahboomcar_ros2_ws/software/library_ws/install/robot_localization/share/robot_localization/params/ekf_x1_x3.yaml.bak`
3. **LiDAR Launch File:** `/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_nav/launch/laser_bringup_launch.py.bak`

## Restoring Backups
To revert to the original settings, run the following commands on the Jetson:
```bash
# Revert EKF parameters
cp /root/yahboomcar_ros2_ws/software/library_ws/src/robot_localization/params/ekf_x1_x3.yaml.bak /root/yahboomcar_ros2_ws/software/library_ws/src/robot_localization/params/ekf_x1_x3.yaml
cp /root/yahboomcar_ros2_ws/software/library_ws/install/robot_localization/share/robot_localization/params/ekf_x1_x3.yaml.bak /root/yahboomcar_ros2_ws/software/library_ws/install/robot_localization/share/robot_localization/params/ekf_x1_x3.yaml

# Revert LiDAR bringup static transform
cp /root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_nav/launch/laser_bringup_launch.py.bak /root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_nav/launch/laser_bringup_launch.py
```

## Parameter Comparison (Side-by-Side)

### EKF `odom0_config` (Wheel Encoders)
* **Old (Manufacturer):** `[true, true, false, false, false, true, true, true, false, false, false, true, false, false, false]`
* **New (Current):** `[true, true, false, false, false, true, true, true, false, false, false, true, false, false, false]`
* *Diff:* Fuses encoders absolute yaw and velocity (keeps wheel odometry active as the main and only state estimator).

### EKF `imu0_config` (Madgwick Integrated IMU)
* **Old (Manufacturer):** `[false, false, false, false, false, true, false, false, false, false, false, true, false, false, false]`
* **New (Current):** `[false, false, false, false, false, false, false, false, false, false, false, false, false, false, false]`
* *Diff:* Disables IMU absolute yaw and yaw velocity completely (sets them to `false`) due to motor vibration noise corrupting measurements during motion.

### LiDAR Static Transform (`laser_bringup_launch.py`)
* **Old:** `arguments = ['0.0435', '5.258E-05', '0.11', '3.14', '0', '0', 'base_link', 'laser']` (180 degrees)
* **Calibrated:** Set the 4th argument (yaw in radians) to rotate the laser scan and align it with the map.
  * For $15^\circ$ clockwise adjustment (subtract $0.26$ rad): use `2.88`
  * For $15^\circ$ counter-clockwise adjustment (add $0.26$ rad): use `3.40`

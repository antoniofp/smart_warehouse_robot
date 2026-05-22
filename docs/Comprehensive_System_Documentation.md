# Comprehensive System Documentation: Rosmaster R2 Smart Warehouse Project

This document serves as the primary onboarding and operational guide for the Rosmaster R2 (Jetson Nano) stack. It combines the original developer documentation with new insights discovered regarding the Docker environment and ROS 2 workspace architecture.

---

## 1. Networking & SSH Access
To control the robot without a monitor, you must connect via Secure Shell (SSH).

### Finding the Robot's IP
*   **LCD Screen:** The most reliable way is to check the small OLED/LCD screen on the robot chassis upon startup; it will display the current IP address.
*   **Terminal:** Alternatively, run `hostname -I` on the Jetson terminal.
*   *Note: Typically, the IP will look like 192.168.1.X or 10.0.0.X depending on your local network.*

### Connecting via SSH
From your main computer (on the same Wi-Fi):
```bash
ssh jetson@<JETSON_IP_ADDRESS>
# Username: jetson
# Password: yahboom
```

---

## 2. Docker & Filesystem Architecture

The ROS 2 Foxy environment is containerized to ensure hardware compatibility and environment consistency. We use the `beautiful_snyder` container.

### Managing the Container
Run these from the Jetson (Host) terminal:
- **Start:** `docker start beautiful_snyder`
- **Enter:** `docker exec -it beautiful_snyder bash`
- **Stop:** `docker stop beautiful_snyder`

### Volume Mapping (Host ↔ Container)
The container filesystem is partially linked to the Jetson host. Changes made in linked folders persist even if the container is deleted.

| Host Path | Container Path | Purpose |
| :--- | :--- | :--- |
| `~/smart_warehouse_robot` | `/root/smart_warehouse_robot` | **Primary Workspace** (Your custom code) |
| `~/maps` | `/root/maps` | Saved SLAM maps |
| `~/rosboard` | `/root/rosboard` | Web dashboard source |
| `~/temp` | `/root/yahboomcar_ros2_ws/temp` | Temporary file portal |

**⚠️ Critical Rule:** Always save your custom nodes and logic inside `/root/smart_warehouse_robot`. Any files saved in other directories (like `/root/yahboomcar_ros2_ws`) are internal to the container and will be lost if the container is recreated.

### The "Workspace-within-a-Workspace" Mystery
You may notice a nested folder structure in the factory code. This is due to Yahboom's repository organization:
*   **Master Repo:** `/root/yahboomcar_ros2_ws` (A Git repository containing AI demos, docs, and software).
*   **Actual Workspace:** `/root/yahboomcar_ros2_ws/yahboomcar_ws` (The functional ROS 2 workspace containing the `src`, `build`, and `install` folders for the robot).

---

## 3. Environment Setup & Overlays (The 4 Layers)

The system uses a **4-Layer Overlay** architecture. Each layer provides specific functionality. You must source them in every new terminal:

1.  **Base Layer (`/opt/ros/foxy/setup.bash`):**
    - **What it provides:** Standard ROS 2 Foxy libraries (`rclcpp`, `rclpy`), common messages (`geometry_msgs`), and core tools (`ros2 cli`, `rviz2`).
2.  **Library Workspace (`/root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash`):**
    - **What it provides:** Low-level device drivers.
    - **Key Packages:** `sllidar_ros2` (LiDAR), `astra_camera` (Depth Camera).
3.  **Main Workspace (`/root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash`):**
    - **What it provides:** Yahboom's robot-specific logic and configuration.
    - **Key Packages:** `yahboomcar_bringup` (Robot start scripts), `yahboomcar_description` (3D URDF models), `yahboomcar_nav` (Navigation and mapping launch files).
4.  **Project Workspace (`/root/smart_warehouse_robot/install/setup.bash`):**
    - **What it provides:** Your custom code and project-specific patches.
    - **Key Packages:** Custom navigation nodes and the **patched `slam_toolbox`** (built from source to fix Jetson memory bugs).

### Persistent Hardware Configuration
Hardware settings are managed via environment variables in `/root/.bashrc`. If you switch sensors or robots, these must be updated:
*   `ROS_DOMAIN_ID=32` (Ensures your robot doesn't interfere with others on the same network)
*   `ROBOT_TYPE=r2` (r2, x1, x3)
*   `RPLIDAR_TYPE=a1` (a1, s2, 4ROS)
*   `CAMERA_TYPE=astraplus` (astrapro, astraplus)

---

## 4. Hardware Bringup (Starting the Robot)

Run each of these in a separate terminal pane or tmux window:

### A. Base Node (Motor Controller & Odometry)
*   **Command:** `ros2 launch yahboomcar_bringup yahboomcar_bringup_R2_launch.py`
*   **Function:** Establishes the serial bridge to the STM32 for motor control and `/odom` publishing.

### B. LiDAR (RPLidar A1)
*   **Command:** `ros2 run sllidar_ros2 sllidar_node --ros-args -p serial_port:=/dev/ttyUSB0 -p serial_baudrate:=115200 -p frame_id:=laser`
*   *Note: Requires 115200 baud rate for the A1 model.*

### C. Depth Camera (Orbbec Astra)
The Astra camera provides two distinct streams:
1.  **Depth/IR Stream:** `ros2 launch astra_camera astra.launch.xml` (Handled via OpenNI).
2.  **Color (RGB) Stream:**
    ```bash
    ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv"
    ```

#### Technical Rationale for RGB Camera Settings:
*   **`video_device:="/dev/video0"`:** The Astra's RGB sensor is a standard UVC-compliant webcam device. While depth is handled by specialized drivers, the color feed appears as a standard video device.
*   **`pixel_format:="yuyv"`:** We force YUYV because the default MJPEG compression often causes decoding bottlenecks or stability issues with the `usb_cam` driver on the Jetson Nano's architecture. YUYV provides a stable, raw stream.
*   **Separation:** We launch RGB separately from the depth driver to avoid resource contention and because the `astra_camera` package's internal RGB handling is often less reliable than the standard `usb_cam` node for standard vision tasks (like YOLO).

---

## 5. CLI Tools & Visualization

### Data Verification
*   **Check topics:** `ros2 topic list`
*   **Check frequency:** `ros2 topic hz /camera/depth/image_raw`
*   **Echo odometry:** `ros2 topic echo /odom`

### Manual Control
*   **Drive Forward:**
    `ros2 topic pub -1 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"`
*   **Teleop Keyboard:**
    `ros2 run teleop_twist_keyboard teleop_twist_keyboard`

### Web Visualization (ROSboard)
If you cannot run GUI tools like RViz over SSH:
1.  `cd /root/rosboard`
2.  `./run`
3.  Visit `http://<JETSON_IP_ADDRESS>:8888` in your laptop browser.

---

## 6. System History & Patches Applied

1.  **USB Device Permissions (Host OS):**
    *   Added udev rule at `/etc/udev/rules.d/56-orbbec-usb.rules` for Astra Camera (Vendor ID 2bc5).
    *   User Permissions: Executed `sudo chmod 666 /dev/ttyUSB*` to allow Docker non-root access to serial ports.
2.  **Boot Order Fix:** Modified `/boot/extlinux/extlinux.conf` to prioritize the SD Card over the SSD.
3.  **STM32 Firmware Bootloop (Hardware):**
    *   **Problem:** Original firmware crashed looking for MPU9250 IMU.
    *   **Fix:** Flashed V3.5.1 firmware via Windows mcuisp tool to support the ICM-20948 IMU found on V2.0 expansion boards.
4.  **Filesystem Optimization:**
    *   Removed ~435MB of redundant core dumps from the root filesystem.
    *   Cleaned up accidental `/build` and `/install` folders in the container's root directory.

## 8. Available Built-in Tools and AI Packages
The Yahboom workspace comes pre-loaded with numerous advanced packages including Nav2 (AMCL), MediaPipe (Google AI), and Lidar-tracking nodes. For a complete list of these hidden capabilities and how to use them without writing custom code, see the [YAHBOOM_WORKSPACE_AUDIT.md](./YAHBOOM_WORKSPACE_AUDIT.md).

## 7. Troubleshooting & Critical Patches

### A. SLAM Toolbox Crash (Exit Code -7 / SIGBUS)
- **Problem:** When running the default `slam_toolbox` package on Jetson Nano (ARM64), the process dies instantly. This is due to a memory alignment bug in the pre-compiled `FastRTPS` middleware and the `Ceres` solver binaries.
- **Fix 1 (Middleware):** We switched from the default middleware to CycloneDDS. This is now permanent in `.bashrc`:
  ```bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  ```
- **Fix 2 (Source Build):** The `slam_toolbox` package was cloned into `/root/smart_warehouse_robot/src` and compiled natively on the Jetson. This ensures the binary is perfectly aligned for the local CPU. Always use the version from the Project Workspace overlay.

### B. Localization & Pose Accuracy
For a detailed breakdown of how the robot calculates its real-world position using EKF and SLAM, see [SLAM_LOCALIZATION_ANALYSIS.md](./SLAM_LOCALIZATION_ANALYSIS.md). This document explains why relying solely on `/odom` is insufficient for precise warehouse tasks.

---

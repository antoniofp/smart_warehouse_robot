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

The ROS 2 Foxy environment is containerized to ensure hardware compatibility and environment consistency.

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

## 3. Environment Setup & Overlays

The system uses a **4-Layer Overlay** architecture. Each layer builds upon the previous one. In every new terminal, you must source the layers in order:

1.  **Base Layer:** Standard ROS 2 Foxy.
    `source /opt/ros/foxy/setup.bash`
2.  **Library Workspace:** Low-level hardware drivers (LIDAR, Camera).
    `source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash`
3.  **Main Workspace:** Factory robot logic and Yahboom packages.
    `source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash`
4.  **Project Workspace:** Your custom warehouse navigation logic.
    `source /root/smart_warehouse_robot/install/setup.bash`

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
*   **Command:** `ros2 launch astra_camera astra.launch.xml`

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

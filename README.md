# Smart Warehouse Robot

Autonomous warehouse navigation system based on **ROS 2 Foxy**, utilizing the **Yahboom Rosmaster R2** (Jetson Nano) platform. This project aims to implement intelligent mapping and navigation within a warehouse environment.

## 🚀 Project Overview

This repository contains the custom development nodes, launch configurations, and documentation for the Smart Warehouse Robot project. The system is designed to run within a containerized environment to ensure consistency and ease of deployment.

## 🛠 Hardware Specifications

*   **Platform:** Yahboom Rosmaster R2
*   **Compute:** NVIDIA Jetson Nano
*   **LIDAR:** RPLidar A1
*   **Depth Camera:** Orbbec Astra
*   **Controller:** STM32-based motor controller with IMU (ICM-20948)

## 📂 Repository Structure

```text
smart_warehouse_robot/
├── src/                # Custom ROS 2 packages (Your code goes here!)
├── docs/               # Technical documentation, guides, and PDFs
├── README.md           # Main project entry point
└── .gitignore          # ROS 2 & Python ignore rules
```

## 📖 System Documentation
For a deep dive into the Docker filesystem, hardware configurations, and the ROS 2 workspace architecture we discovered, see:
👉 **[Comprehensive System Documentation](docs/Comprehensive_System_Documentation.md)**

## 🐳 Docker Setup

The project environment is pre-configured inside a Docker container. Use the following commands to start and enter the environment from the Jetson terminal:

```bash
# Start the container
docker start beautiful_snyder

# Enter the container (Open a new shell)
docker exec -it beautiful_snyder bash
```

## ⚙️ Environment Setup (The 4 Layers)

The system uses a **4-Layer Overlay** architecture. You must source these layers in every new terminal to access the specific nodes and launch files they provide.

| Layer | Source Command | Purpose / Contents |
| :--- | :--- | :--- |
| **1. Base** | `source /opt/ros/foxy/setup.bash` | Standard ROS 2 Foxy core. |
| **2. Library** | `source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash` | Hardware drivers (Lidar, Camera). |
| **3. Main** | `source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash` | Robot models, Yahboom bringup & nav logic. |
| **4. Project** | `source /root/smart_warehouse_robot/install/setup.bash` | Your custom code & patched `slam_toolbox`. |

---

## ⚡ Automated Startup (Recommended)

To quickly start all necessary nodes (ROSboard, Foxglove, Hardware Bringup, RGB Camera, and SLAM) with a single command:

**For Mapping (Building a new map):**
```bash
./start_mapping.sh
```

**For Localization (Navigating a known map with SLAM Toolbox):**
```bash
./start_localization.sh
```

**For Full Autonomous Navigation (AMCL + Nav2 + TEB):**
```bash
./start_navigation.sh
```

These scripts handle environment sourcing, set the correct DDS implementation, and manage the background processes for you. Press **Ctrl+C** to stop all nodes.

---

## 🚦 Quick Start Guide (Manual)

Follow these steps in separate terminals inside the Docker container.

### Step 1: Hardware Bringup
Connects to the motors, Lidar, and Camera.
*   **Requires:** Layers 1, 2, and 3.

**Base & Lidar:**
```bash
ros2 launch yahboomcar_nav laser_bringup_launch.py
```

**RGB Camera (Color Feed):**
```bash
ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv"
```

### Step 2: SLAM Mapping OR Localization
Starts the mapping engine to build a 2D floor plan, or localization mode to navigate one.
*   **Requires:** Layers 1, 2, 3, and 4.
*   **Note:** We use `CycloneDDS` to prevent memory crashes on the Jetson.

**Mapping:**
```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch slam_toolbox online_async_launch.py
```

**Localization:**
```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch slam_toolbox localization_launch.py
```

### Step 3: Visualization (RViz)
Opens a pre-configured RViz window to see the robot and the map.
*   **Requires:** Layers 1, 2, and 3.
```bash
ros2 launch yahboomcar_description display_R2.launch.py
```

## 🎮 Tools & Manual Control
*   **Teleop Control:** `ros2 run teleop_twist_keyboard teleop_twist_keyboard`
*   **Web Visualization (ROSboard):** 
    1.  `cd /root/rosboard && ./run`
    2.  Access via: `http://<JETSON_IP_ADDRESS>:8888`
*   **Modern Web UI (Foxglove):**
    1. `ros2 launch rosbridge_server rosbridge_websocket_launch.xml`
    2. Access via: `ws://<JETSON_IP_ADDRESS>:9090` in the Foxglove app.
*   **Initial Pose (SLAM Localization):** Update `map_start_pose` in `src/slam_toolbox/config/mapper_params_localization.yaml` before launching to ensure the pose transform is correct.

---

## 🛠 Troubleshooting

### SLAM Map Saving Timeout
If `ros2 run nav2_map_server map_saver_cli` fails with a timeout, it is likely due to a QoS mismatch (slam_toolbox uses `transient_local` durability).

**Fix:** Add the following parameter to the command:
```bash
ros2 run nav2_map_server map_saver_cli -f /root/maps/my_map --ros-args -p map_subscribe_transient_local:=true
```

### Docker and X11 GUI Applications (e.g., RViz)
When running ROS2 GUI applications like `rviz2` or `joint_state_publisher_gui` from within a Docker container on the Jetson Nano, you might encounter the following error:
```
qt.qpa.xcb: could not connect to display :0
No protocol specified
```

**Workaround:**
This error occurs because the Docker container does not have permission to communicate with the host's X11 server. To fix this, you need to grant local connections access to the X server from the host system.

1. Open a terminal directly on the host machine (Jetson Nano) **outside** of the Docker container.
2. Run the following command to allow local connections:
   ```bash
   xhost +local:root
   ```
   *(You should see a message saying "non-network local connections being added to access control list")*
3. Inside the Docker container, ensure your display environment variable is set correctly before launching your ROS2 application:
   ```bash
   export DISPLAY=:0
   ros2 launch yahboomcar_description display_R2.launch.py
   ```
> **Note:** The `xhost +local:root` command resets upon a reboot of the host machine. You will need to run it again after restarting the Jetson Nano.


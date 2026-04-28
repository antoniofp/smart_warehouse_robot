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
├── src/                # Custom ROS 2 packages
├── docs/               # Technical documentation and PDFs
├── README.md           # Main documentation
└── .gitignore          # ROS 2 & Python ignore rules
```

## ⚙️ Environment Setup

The project operates across three primary ROS 2 workspaces. In every new terminal, you must source the base environments:

### 1. Library Workspace (Drivers)
```bash
source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash
```

### 2. Main Workspace (Yahboom Logic)
```bash
source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
```

### 3. Project Workspace (Your Logic)
From the root of this repository:
```bash
colcon build
source install/setup.bash
```

## 🚦 Hardware Bringup

Run each of these in a separate terminal:

### A. Base Node (Motors & Odometry)
```bash
ros2 launch yahboomcar_bringup yahboomcar_bringup_R2_launch.py
```

### B. LIDAR (RPLidar A1)
```bash
ros2 run sllidar_ros2 sllidar_node --ros-args -p serial_port:=/dev/ttyUSB0 -p serial_baudrate:=115200 -p frame_id:=laser
```

### C. Depth Camera (Astra)
```bash
ros2 launch astra_camera astra.launch.xml
```

## 🎮 Tools & Visualization

*   **Teleop Control:** `ros2 run teleop_twist_keyboard teleop_twist_keyboard`
*   **Web Visualization (ROSboard):** 
    1.  `cd /root/rosboard && ./run`
    2.  Access via: `http://<JETSON_IP_ADDRESS>:8888`

---


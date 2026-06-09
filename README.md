# Smart Warehouse Robot

Autonomous warehouse navigation system based on **ROS 2 Foxy**. This project implements a distributed architecture where a generic ROS 2 robot handles intelligent navigation while an off-board host PC processes AI vision.

## System Architecture

This project uses a split processing architecture to maximize the robot's hardware performance:
1. **Robot**: Handles Hardware Bringup, SLAM, Nav2 Pure Pursuit, HTTP Video Streaming, and the Mission State Machine.
2. **Host PC**: Connects to the robot's camera stream, runs YOLOv8 inference, and sends real-time obstacle detections back to the robot via a zero-lag UDP socket (Port 5005).

## Repository Structure

```text
smart_warehouse_robot/
├── models/             # YOLOv8 Neural Network weights (e.g., best.pt)
├── scripts/            # Core Python nodes
│   ├── mission_vision.py    # Robot: UDP Receiver & Mission Controller
│   └── pc_vision_node.py    # Host PC: YOLOv8 Inference Node
├── src/                # Custom ROS 2 packages and Nav2 parameters
├── utils/              # Diagnostic scripts, fixes, and tests
├── start_*.sh          # Auxiliary ROS 2 launch scripts
└── docs/               # Technical documentation
```

---

## How to Run the Smart Mission

To start the autonomous workflow, the robot's logic must be executed on the robot itself, and the AI vision node on the Host PC.

### 1. On the Robot
Launch the unified mission script. This will start SLAM, the Nav2 stack, the video stream, and the UDP Listener.
```bash
./start_mission.sh
```

### 2. On the Host PC
Ensure the YOLO environment is set up properly. Run the vision node to start analyzing the warehouse environment:
```bash
python3 scripts/pc_vision_node.py
```

---

## Utility Scripts

The repository includes several `start_*.sh` scripts in the root directory to facilitate ROS 2 lifecycle management.

*   `start_mission.sh`: Main entry point. Starts SLAM localization, Nav2, Video streaming, Foxglove, and the UDP listener.
*   `start_slam_navigation.sh`: Starts Navigation paired with SLAM Toolbox Localization.
*   `start_navigation.sh`: Starts standard Navigation paired with AMCL.
*   `start_mapping.sh`: Starts the SLAM Toolbox in mapping mode to create a new floor plan.
*   `save_map.sh`: Utility to easily save a newly created map (e.g., `./save_map.sh my_new_map`).
*   `send_goal.sh`: Allows sending a specific navigation goal from the command line.
*   `kill_all_ros.sh`: Emergency kill switch. Safely terminates all running ROS 2 nodes, video streams, and python scripts.

### Manual Teleoperation
If manual control of the robot is required at any point, use the teleop node:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### Saving a Map
If `./start_mapping.sh` was used to create a new map, it can be saved easily by running the included utility script before shutting down the mapping nodes:
```bash
./save_map.sh my_new_map
```

---

## Smart Vision Rules & Logistics

The Host PC continuously analyzes the camera feed and sends triggers to the Robot. The robot dynamically reacts to the following state changes:

*   **Pedestrian Zone**: Drastically reduces linear speed and adjusts the pure pursuit lookahead distance to safely navigate around humans without oscillating.
*   **Restricted Area**: Automatically skips the current waypoint and recalculates the route.
*   **Loading Zone**: Halts the robot completely and waits for the user to send a `continue` signal to resume the mission.
*   **Stop for Safety**: Performs an emergency halt for 5 seconds before resuming automatically.
*   **Robots-Only Zone**: Restores navigation speed and lookahead distance to 100% nominal.
*   **Parking Zone**: Halts the robot and safely initiates the shutdown sequence for the ROS 2 nodes.

---

## Visualization and Monitoring

The system is pre-configured with modern monitoring tools to observe the robot's state from any computer on the network:
*   **Foxglove Studio**: Enabled by default in the launch scripts. Connect to `ws://<ROBOT_IP>:9090` using the Foxglove application to view live maps, topics, and telemetry.
*   **ROSboard**: An alternative web-based visualizer. It is disabled by default to save resources, but can be enabled in the `.sh` launch files if needed.

---

## Optional Docker Setup

If containerizing the robot's environment is desired, ensure the workspace is mounted properly.
```bash
# Example command to start and enter the container
docker start <your_container_name>
docker exec -it <your_container_name> bash
```
*(Note: If deploying this code on our original Jetson Nano configuration, the container name is `beautiful_snyder`)*

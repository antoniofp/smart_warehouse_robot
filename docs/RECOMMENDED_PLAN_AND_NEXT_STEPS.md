# Recommended Plan & Next Steps: Smart Warehouse Robot

Based on the audit of the R2 hardware, the ROS 2 workspace, and the user's progress with YOLOv8, here is the recommended operational roadmap.

## Phase 1: Robust Mapping (No Code Required)
The current SLAM Toolbox setup is functional but susceptible to "Odometry Slip" (loop closure failures) during fast rotations or in highly symmetrical environments (like long, featureless hallways).

**Next Steps:**
1. Clear the environment and place distinct obstacles (boxes, chairs) against symmetrical walls to provide Lidar "anchors."
2. Launch `./start_mapping.sh`.
3. Teleoperate the robot **slowly**, especially during turns, to prevent wheel slip from corrupting the odometry.
4. Once the map on ROSboard is complete and accurate, save it using the map server:
   ```bash
   ros2 run nav2_map_server map_saver_cli -f /root/maps/warehouse_v1
   ```

## Phase 2: Autonomous Navigation (AMCL + TEB)
Relying purely on `/odom` is dangerous due to drift. We must transition from mapping to localization. Furthermore, the R2 uses **Ackerman steering** (car-like), meaning it cannot rotate in place. The standard Nav2 DWA planner will fail.

**Next Steps:**
1. Launch the navigation stack using the **TEB (Timed Elastic Band)** local planner, which respects the mechanical turning radius of the R2:
   ```bash
   ros2 launch yahboomcar_nav navigation_teb_launch.py map:=/root/maps/warehouse_v1.yaml
   ```
2. Open RViz and use the **2D Pose Estimate** tool to give AMCL an initial guess of where the robot is on the map.
3. Use the **Nav2 Goal** tool in RViz to command the robot. Ensure it can autonomously drive from point A to B while smoothly navigating around obstacles like a car.

## Phase 3: YOLO Integration (AI Autonomy)
With the robot capable of moving safely on its own, we can introduce the custom YOLO models.

**Next Steps:**
1. Run the custom YOLO inference script on the host GPU.
2. The script should subscribe to the camera feed (or use OpenCV to grab `/dev/video0`).
3. When YOLO detects a target (e.g., "Stop Sign" or "Pallet A"), the Python script should interface with the Nav2 Action Server (`NavigateToPose`). 
4. **Example Logic:** If the sign is detected, cancel the current Nav2 goal and command the robot to halt, or publish a new goal coordinate to navigate towards the detected object.

*Note: For lightweight tasks (like hand tracking or following lines), refer to the pre-compiled tools in `yahboomcar_mediapipe` and `yahboomcar_visual` (see `YAHBOOM_WORKSPACE_AUDIT.md`) as they run efficiently without requiring the complex YOLO/PyTorch environment.*
# Recommended Plan & Next Steps: Smart Warehouse Presentation

This document outlines the detailed, step-by-step roadmap for the final presentation of the Smart Warehouse Robot. It strictly adheres to operational constraints: **No RViz (headless operation only), remote initialization, and Custom YOLO-driven autonomy.**

---

## Phase 1: Creating the "Golden Map"
SLAM is sensitive to featureless environments (like symmetrical mazes). We must create one perfect, static map to be used for all future navigation.

**Execution Steps:**
1.  **Prepare the Maze:** If the maze is completely symmetrical, temporarily place a few distinct, non-symmetrical objects (e.g., a box) near the starting area to help SLAM anchor the loop closures.
2.  **Launch SLAM Headless:** Run `./start_mapping.sh`.
3.  **Teleoperate Smoothly:** Use the keyboard teleop to drive the maze. **Critical:** Drive slowly and make wide, smooth turns. Fast rotations cause odometry slip, which destroys the SLAM map.
4.  **Verify Remotely:** Monitor the map generation on **ROSboard** (`http://<ROBOT_IP>:8888`). Do not use RViz.
5.  **Save the Map:** Once the map is visually perfect on ROSboard, save it from the terminal:
    ```bash
    ros2 run nav2_map_server map_saver_cli -f /root/maps/final_maze --ros-args -p map_subscribe_transient_local:=true
    ```
6.  **Kill SLAM:** Stop `./start_mapping.sh`. You will not use SLAM Toolbox again for the presentation.

---

## Phase 2: Headless Localization & Navigation (AMCL + TEB)
For the presentation, the robot must localize itself without a monitor or RViz. We will use the static map, AMCL for localization, and the TEB planner for Ackerman steering.

**Execution Steps:**
1.  **Launch Nav2 Stack:**
    ```bash
    ros2 launch yahboomcar_nav navigation_teb_launch.py map:=/root/maps/final_maze.yaml
    ```
2.  **Headless Initial Pose Initialization:**
    Since we cannot use the RViz "2D Pose Estimate" button, we must define the starting point via the terminal. Place the robot in an agreed-upon "Starting Zone" in the physical maze, then publish its exact coordinates on the map:
    ```bash
    ros2 topic pub --once /initialpose geometry_msgs/msg/PoseWithCovarianceStamped "{header: {frame_id: 'map'}, pose: {pose: {position: {x: 0.0, y: 0.0, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
    ```
    *(Note: You will need to determine the exact X, Y, and quaternion values of your physical starting box based on the generated map's origin).*
3.  **Headless Goal Testing:** Test the TEB planner by sending a destination coordinate via terminal to ensure it navigates without crashing:
    ```bash
    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 0.0, z: 0.0}, orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}}}}"
    ```

---

## Phase 3: YOLO-Driven Autonomy (The Final Mission)
The ultimate goal is for the robot to navigate the maze autonomously, reacting to custom traffic/warehouse signs detected by your YOLOv8 model running on the host GPU.

### Scenario A: The "Wander and React" Logic
If the exact parking spot is unknown, the robot must explore safely until YOLO finds the target.
1.  **Wandering Script:** Write a simple Python node that sends a sequence of `NavigateToPose` goals (Waypoints) representing the intersections of the maze.
2.  **YOLO Interruption:** Your YOLO script monitors `/dev/video0`.
3.  **The Trigger:** When YOLO detects the "Parking Spot Sign" with high confidence:
    *   The Python script immediately cancels the current Nav2 goal (`action_client.cancel_goal_async()`).
    *   It calculates a new local goal right in front of the sign and sends it to TEB to park the robot.

### Scenario B: The "Preloaded Route with Sign Verification"
If the path is defined, but signs dictate behavior (e.g., a "Stop" sign or "Detour" sign).
1.  **Route Execution:** A Python node feeds an exact array of coordinates to the robot.
2.  **Sign Interaction:** 
    *   If YOLO sees "Stop", send a 0 velocity command to `/cmd_vel` or pause the Nav2 action.
    *   If YOLO sees "Parking Zone", execute the docking maneuver.

**Key Architecture Takeaway:** Your custom YOLO Python script is the "Brain." It watches the camera and acts as the master commander, sending action goals to Nav2. Nav2 (AMCL + TEB) is the "Spinal Cord," ensuring the robot doesn't hit walls while trying to obey the Brain.

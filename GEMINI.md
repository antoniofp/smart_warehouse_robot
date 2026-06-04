# Project Instructions: Smart Warehouse Robot

## General Workflows
- **Always suggest a `git push`** after making changes to the codebase and committing them.

## AI Remote Development & Synchronization (SSH)

This workspace uses a remote setup where the AI agent (or user) runs on a fast host PC and controls the Jetson remotely over SSH.

### 1. Synchronization at Start
- **Frequent Pulling:** Pull changes frequently on all machines to prevent drift.
- **Initial Sync Verification:** At the start of every session, the AI agent must run `git pull` on both the host PC and inside the Jetson Docker container, and verify that their commit hashes match. If there is a mismatch, warn the user.
- **Handling Local Changes during Pull:**
  - If there are uncommitted changes on the Jetson container that do not conflict, pull normally.
  - If a merge conflict would occur, use `git stash` to temporarily shelf the changes, run `git pull`, and then `git stash pop`.
  - If conflicts arise after popping the stash, the AI must ask the user which changes should overwrite what (usually favoring the latest changes) and resolve them accordingly.
  - **Detecting Unstaged Changes (Crucial):** At the start of every session, the AI must check for unstaged changes inside the Jetson container. If any exist, the AI must explicitly notify the user with a list of the modified files. The AI must never silently ignore, overwrite, or restore these files; it must ask the user whether to keep, commit, or restore (discard) them.

### 2. Development Workflows
- **Quick Tests / Script Prototyping:**
  - For small edits, quick debugging, or immediate script testing, write/edit files and run commands directly on the Jetson via SSH.
- **Deep Development Sessions:**
  - For writing larger features, refactoring, or modifying multiple files, edit the local clone on the host PC to take advantage of faster local file editing.

### 3. Docker & Git Permissions
- Git operations on the Jetson **must only** be executed inside the `beautiful_snyder` Docker container (which runs as `root` and has GitHub credentials set up) to avoid permission errors on the host.
  - *Example:* `ssh jetson-desktop "docker exec beautiful_snyder bash -c 'cd /root/smart_warehouse_robot && git pull'"`

### 4. Porting and Pushing Changes
When saving working changes, the AI should choose the most efficient workflow:
- **Files Outside the Repo:** If changes were made to files *outside* the repository on the Jetson (e.g. `.bashrc` or global system configs), **do not** attempt to push them to git. Instead, document these changes in `README.md` or `GEMINI.md` if they are relevant to the robot's setup.
- **Scenario A (Mostly Host Changes):** If most repository modifications were made in the host clone with only minor SSH tweaks on the Jetson:
  1. Port the Jetson repository tweaks back to the host clone.
  2. Commit and push from the host PC.
  3. Pull inside the Jetson container.
- **Scenario B (Mostly Jetson Changes):** If most repository modifications were made directly on the Jetson via SSH:
  1. Commit and push directly from inside the Jetson container.
  2. Pull the changes to the host clone.
  3. Merge and push any remaining host-side changes.

## Automated Startup
- **Mapping Script:** `./start_mapping.sh` (Starts ROSboard, Bringup, Camera, and SLAM with CycloneDDS).

## Environment Sourcing
The workspace uses 4 layers. Source in order:
1. `source /opt/ros/foxy/setup.bash`
2. `source /root/yahboomcar_ros2_ws/software/library_ws/install/setup.bash`
3. `source /root/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash`
4. `source /root/smart_warehouse_robot/install/setup.bash` (after building)

## Background Tasks
Manage long-running nodes (like ROSboard or the camera) in the background using `&` or a terminal multiplexer like `screen`/`tmux`.

## Hardware Bringup
- **Consolidated (Base + Lidar):** `ros2 launch yahboomcar_nav laser_bringup_launch.py`
- **RGB Camera (USB):** `ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv"`

## SLAM & Mapping
- **Command:** `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && ros2 launch slam_toolbox online_async_launch.py`
- **Note:** Ensure `use_sim_time` is correctly set if you experience map distortion or timing issues.
- **Saving a Map:** Once mapping is complete, DO NOT kill the SLAM node immediately. Run:
  `ros2 run nav2_map_server map_saver_cli -f /root/maps/my_warehouse_map --ros-args -p map_subscribe_transient_local:=true`

## Navigation (Nav2 & SLAM Localization)
- **TEB Planner (Crucial for R2 Ackerman Steering):** Do NOT use the default DWA planner. Use TEB to respect the steering radius constraints.
- **Custom Behavior Tree:** We use `src/r2_nav/behavior_trees/minimal_bt.xml` which includes a `RecoveryNode` and `ClearEntireCostmap` to handle obstacles more robustly.
- **Localization:** We use SLAM Toolbox in Localization mode.
- **Startup Scripts:**
  - `./start_localization.sh`: Starts SLAM Toolbox in localization mode using the saved map.
  - `./start_navigation.sh`: Full navigation stack including AMCL localization, Nav2 with TEB planner, and custom Behavior Tree.
- **Map Location:** Perfect maps are stored in `src/r2_nav/maps/`. Update the `map_file_name` in `src/slam_toolbox/config/mapper_params_localization.yaml` if you create a new map.

## Visualization & Headless Operation
- **Presentation Constraint (NO RVIZ):** Do NOT use RViz for operation or initialization due to resource overhead and HDMI requirements. 
- **Remote Monitoring:**
  - **ROSboard:** Access at `http://<IP>:8888`
  - **Foxglove:** Access at `ws://<IP>:9090`
- **Initial Pose:**
  - Do NOT publish to `/initialpose` at runtime as it can corrupt the SLAM scan matching.
  - **Correct Method:** Edit the `map_start_pose` parameter in `src/slam_toolbox/config/mapper_params_localization.yaml` before launching the localization script.

## Hardware Calibration (Front Steering & Odometry)
We modified the manufacturer's Yahboom repository (located at `/root/yahboomcar_ros2_ws/yahboomcar_ws/` inside the Jetson container) to support runtime turning and steering calibration without rebuilding:
- **Steering Offset**: Added a ROS 2 parameter `steering_offset` (in degrees) to `Ackman_driver_R2.py`. This applies a calibration offset to both the command (steer wheels straight) and the feedback (report true physical angle to odometry).
- **Steering Scale**: Exposed the parameter `linear_scale_y` to scale the turning calculations in the odometry node.
- **Top-Level Launch Files**: Updated `yahboomcar_bringup_R2_launch.py` and `laser_bringup_launch.py` to propagate these arguments down to the driver and odometry base nodes.
- **Usage**: Both values can be adjusted dynamically in the startup script `./start_navigation.sh` via the `STEERING_OFFSET` and `STEERING_SCALE` variables.

# Project Instructions: Smart Warehouse Robot

## General Workflows
- **Always suggest a `git push`** after making changes to the codebase and committing them.

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

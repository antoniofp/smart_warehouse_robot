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
See `background_tasks.md` for guidelines on managing long-running nodes.

## Hardware Bringup
- **Consolidated (Base + Lidar):** `ros2 launch yahboomcar_nav laser_bringup_launch.py`
- **RGB Camera (USB):** `ros2 run usb_cam usb_cam_node_exe --ros-args -p video_device:="/dev/video0" -p pixel_format:="yuyv"`

## SLAM & Mapping
- **Troubleshooting:** See `slam_troubleshooting.md` for fixes regarding map distortion and `use_sim_time`.
- **Command:** `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp && ros2 launch slam_toolbox online_async_launch.py`

## Visualization & Tools
- **ROSboard:** `cd /root/rosboard && ./run` (Access at `http://<IP>:8888`)
- **RViz:** `ros2 launch yahboomcar_description display_R2_launch.py` (Requires `xhost +local:root` on host)

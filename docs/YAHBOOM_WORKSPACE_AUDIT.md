# Yahboom Workspace Audit: Hidden Tools and Capabilities

During a deep audit of the `/root/yahboomcar_ros2_ws` container workspace, we discovered several advanced packages and nodes provided by Yahboom. These tools can significantly accelerate development by bypassing the need to compile complex AI or navigation stacks from scratch.

## 1. Navigation and Localization (AMCL)
**Package:** `yahboomcar_nav`

While the default startup scripts only launch SLAM (mapping), the workspace contains full configurations for **Nav2** and **AMCL** (Monte Carlo Localization).
*   **Key File:** `launch/navigation_dwa_launch.py`
*   **Capabilities:** Once a map is saved, this script launches the map server, AMCL for probabilistic localization, and the DWA (Dynamic Window Approach) local planner. This is the industry standard for warehouse navigation, allowing the robot to navigate a known map without modifying it (preventing map corruption).

## 2. Artificial Intelligence and Vision
While the workspace contains legacy pre-compiled vision packages, **our primary strategy relies on a custom YOLO deployment running natively on the Jetson Nano host GPU.**

### Custom YOLO (Primary Strategy)
*   **Location:** Outside the container, natively on the host GPU.
*   **Capabilities:** Custom detection of specific warehouse signs (Stop, Parking, Detour) which is impossible with the pre-compiled generic nodes in the workspace.
*   **Integration:** The YOLO Python script will act as the "Brain," processing the video feed and publishing Nav2 commands (`/navigate_to_pose`) based on the recognized custom signs.

### MediaPipe & KCF Tracker (Deprecated/Experimental)
*   **Packages:** `yahboomcar_mediapipe`, `yahboomcar_KCFTracker`
*   **Note:** These packages contain pre-compiled Google AI and OpenCV trackers for hands, faces, and basic objects. **They are not useful for the final presentation** as they cannot detect custom warehouse signs. They remain in the workspace strictly as experimental artifacts or fallbacks for generic object tracking.

### Color and Line Following
**Package:** `yahboomcar_visual` / `yahboomcar_linefollow`
*   **Capabilities:** Classic computer vision (OpenCV) nodes for detecting lines on the floor or tracking specific colors. 

## 3. Lidar-Based Autonomy
**Package:** `yahboomcar_laser`

The RPLidar A1 can be used for more than just mapping. Yahboom includes nodes that use raw laser scans for immediate reactive behaviors.
*   **Interesting Nodes:**
    *   `laser_Avoidance`: The robot drives forward autonomously and steers away from obstacles detected by the Lidar.
    *   `laser_Tracker`: The robot uses the Lidar to find the nearest object (e.g., a person's legs) and follows it dynamically.

## 4. Usage Notes for R2
Many of the launch files in these packages have suffixes like `_X3` or `_X1`. However, the underlying Python scripts are generic. To use them on the R2, you simply need to ensure the topics (like `/camera/color/image_raw` or `/scan`) match the outputs of the R2's specific camera and Lidar bringup scripts.

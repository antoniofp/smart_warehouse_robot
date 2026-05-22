# Yahboom Workspace Audit: Hidden Tools and Capabilities

During a deep audit of the `/root/yahboomcar_ros2_ws` container workspace, we discovered several advanced packages and nodes provided by Yahboom. These tools can significantly accelerate development by bypassing the need to compile complex AI or navigation stacks from scratch.

## 1. Navigation and Localization (AMCL)
**Package:** `yahboomcar_nav`

While the default startup scripts only launch SLAM (mapping), the workspace contains full configurations for **Nav2** and **AMCL** (Monte Carlo Localization).
*   **Key File:** `launch/navigation_dwa_launch.py`
*   **Capabilities:** Once a map is saved, this script launches the map server, AMCL for probabilistic localization, and the DWA (Dynamic Window Approach) local planner. This is the industry standard for warehouse navigation, allowing the robot to navigate a known map without modifying it (preventing map corruption).

## 2. Artificial Intelligence and Vision
Compiling modern AI frameworks (like PyTorch or YOLOv8) on the Jetson Nano's legacy JetPack 4.6.1 is notoriously difficult. This workspace includes pre-compiled, hardware-accelerated alternatives.

### MediaPipe (Google AI)
**Package:** `yahboomcar_mediapipe`
*   **Capabilities:** Real-time, lightweight machine learning for vision.
*   **Interesting Nodes:**
    *   `01_HandDetector.py` / `10_HandCtrl.py`: Detect hands and control the robot's movement via hand gestures.
    *   `04_FaceMesh.py` / `07_FaceDetection.py`: Fast face detection.
    *   `02_PoseDetector.py`: Full body pose estimation.
*   **Why it matters:** It provides immediate AI capabilities without the dependency hell of custom YOLO installations.

### KCF Object Tracking
**Package:** `yahboomcar_KCFTracker`
*   **Capabilities:** Kernelized Correlation Filters for object tracking. You select an object in the camera feed, and the robot will autonomously rotate and drive to keep the object centered in its vision.

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

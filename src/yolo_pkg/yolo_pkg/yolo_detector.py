#!/usr/bin/env python3
import sys
import os

# Pre-load fix for memory issues on Jetson
os.environ['LD_PRELOAD'] = '/lib/aarch64-linux-gnu/libgomp.so.1'

# Add venv site-packages
venv_path = '/root/smart_warehouse_robot/venv_yolo/lib/python3.8/site-packages'
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import time
from ultralytics import YOLO

class YOLODetector(Node):
    def __init__(self):
        super().__init__('yolo_detector')
        
        # Parameters
        self.declare_parameter('model_path', 'yolov5n.pt')
        self.declare_parameter('input_topic', '/image_raw')
        self.declare_parameter('output_topic', '/yolo/image_annotated')
        
        model_path = self.get_parameter('model_path').get_parameter_value().string_value
        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        output_topic = self.get_parameter('output_topic').get_parameter_value().string_value
        
        # Initialize YOLOv5 via Ultralytics (more stable than torch.hub)
        self.get_logger().info(f'Loading model: {model_path}')
        self.model = YOLO(model_path)
        
        # Initialize Bridge
        self.bridge = CvBridge()
        
        # Subscribers and Publishers
        self.subscription = self.create_subscription(Image, input_topic, self.image_callback, 1)
        self.publisher = self.create_publisher(Image, output_topic, 10)
        
        self.get_logger().info('YOLOv5 (Ultralytics) Node Initialized')

    def image_callback(self, msg):
        try:
            # Convert ROS Image message to OpenCV image
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # CPU OPTIMIZATION: Downscale
            small_frame = cv2.resize(cv_image, (320, 320))
            
            start_time = time.time()
            
            # Run inference
            # Using CUDA for better performance on Jetson Nano
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            results = self.model.predict(cv_image, conf=0.25, verbose=False, device=device)
            
            # Log detections to console for debugging
            boxes = results[0].boxes
            if len(boxes) > 0:
                for box in boxes:
                    cls_id = int(box.cls[0])
                    label = self.model.names[cls_id]
                    conf = float(box.conf[0])
                    self.get_logger().info(f"--- FOUND: {label} ({conf:.2f}) ---")
            
            # Annotate
            annotated_frame = results[0].plot()
            
            # Calculate and Draw FPS
            fps = 1.0 / (time.time() - start_time)
            cv2.putText(annotated_frame, f"FPS: {fps:.2f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Publish
            output_msg = self.bridge.cv2_to_imgmsg(annotated_frame, encoding='bgr8')
            self.publisher.publish(output_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = YOLODetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

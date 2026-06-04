#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped
import math

class PoseLogger(Node):
    def __init__(self):
        super().__init__('pose_logger')
        self.subscription = self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self.listener_callback,
            10)
        self.log_file = '/root/smart_warehouse_robot/log/robot_pose.log'

    def listener_callback(self, msg):
        pose = msg.pose.pose
        x = pose.position.x
        y = pose.position.y
        
        # Convertir cuaternión a ángulo Yaw (grados)
        q = pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        yaw_rad = math.atan2(siny_cosp, cosy_cosp)
        yaw_deg = math.degrees(yaw_rad)
        
        try:
            with open(self.log_file, 'w') as f:
                f.write(f'X: {x:.4f}\nY: {y:.4f}\nYAW: {yaw_deg:.2f}\n')
        except Exception:
            pass

def main(args=None):
    rclpy.init(args=args)
    node = PoseLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

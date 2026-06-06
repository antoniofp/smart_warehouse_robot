#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import os

class LidarTimeFixer(Node):
    def __init__(self):
        super().__init__('lidar_time_fixer')
        
        # Nos suscribimos al scan original del coche
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan',
            self.listener_callback,
            10)
            
        # Publicamos el scan corregido en el mismo tópico pero con tiempo actualizado
        self.publisher = self.create_publisher(LaserScan, '/scan_corrected', 10)

    def listener_callback(self, msg):
        # Clonamos el mensaje e inyectamos la hora exacta de ESTE INSTANTE
        corrected_msg = msg
        corrected_msg.header.stamp = self.get_clock().now().to_msg()
        corrected_msg.header.frame_id = "laser"
        
        self.publisher.publish(corrected_msg)

def main(args=None):
    os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'
    os.environ['ROS_DOMAIN_ID'] = '32'
    
    rclpy.init(args=args)
    node = LidarTimeFixer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

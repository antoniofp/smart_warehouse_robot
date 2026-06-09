import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
import time

class ScanDelayNode(Node):
    def __init__(self):
        super().__init__('scan_delay_node')
        self.sub = self.create_subscription(LaserScan, '/scan', self.callback, 10)
        self.count = 0

    def callback(self, msg):
        now = self.get_clock().now()
        msg_time = rclpy.time.Time.from_msg(msg.header.stamp)
        diff_ms = (now.nanoseconds - msg_time.nanoseconds) / 1e6
        print(f'[{self.count}] Scan stamp: {msg.header.stamp.sec}.{msg.header.stamp.nanosec:09d} | Delay: {diff_ms:.2f} ms')
        self.count += 1
        if self.count >= 10:
            raise SystemExit

def main():
    rclpy.init()
    node = ScanDelayNode()
    try:
        rclpy.spin(node)
    except SystemExit:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

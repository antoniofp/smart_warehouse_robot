import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
import math

def yaw_from_quat(q):
    siny_cosp = 2 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)

class OdomImuLogger(Node):
    def __init__(self):
        super().__init__('odom_imu_logger')
        self.odom_sub = self.create_subscription(Odometry, '/odom_raw', self.odom_callback, 10)
        self.imu_sub = self.create_subscription(Imu, '/imu/data', self.imu_callback, 10)
        self.odom_msg = None
        self.imu_msg = None
        self.timer = self.create_timer(0.2, self.timer_callback)

    def odom_callback(self, msg):
        self.odom_msg = msg

    def imu_callback(self, msg):
        self.imu_msg = msg

    def timer_callback(self):
        if self.odom_msg and self.imu_msg:
            oq = self.odom_msg.pose.pose.orientation
            oyaw = yaw_from_quat(oq)
            ovel = self.odom_msg.twist.twist.angular.z
            ovx = self.odom_msg.twist.twist.linear.x
            ovy = self.odom_msg.twist.twist.linear.y

            iq = self.imu_msg.orientation
            iyaw = yaw_from_quat(iq)
            ivel = self.imu_msg.angular_velocity.z

            print(f'Odom Vx: {ovx:.3f} | Odom Vy (Steer): {ovy:.3f} | Odom Yaw: {math.degrees(oyaw):.2f}° | Odom YawVel: {ovel:.4f} | IMU Yaw: {math.degrees(iyaw):.2f}° | IMU YawVel: {ivel:.4f}')

def main():
    rclpy.init()
    node = OdomImuLogger()
    print('Logging Odom and IMU (Ctrl+C to stop)...')
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

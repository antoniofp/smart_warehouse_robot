import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from tf2_ros import TransformException, Buffer, TransformListener

class TfToPose(Node):
    def __init__(self):
        super().__init__('tf_to_pose')
        
        self.publisher = self.create_publisher(PoseStamped, '/pose', 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.timer = self.create_timer(0.05, self.on_timer)
        self.get_logger().info("🔄 [TF2POSE] Conversión de tiempo sincronizado activa.")

    def on_timer(self):
        try:
            t = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
                
            msg = PoseStamped()
            msg.header.stamp = t.header.stamp 
            msg.header.frame_id = 'map'
            
            msg.pose.position.x = t.transform.translation.x
            msg.pose.position.y = t.transform.translation.y
            msg.pose.position.z = t.transform.translation.z
            msg.pose.orientation = t.transform.rotation
            
            self.publisher.publish(msg)
            
        except TransformException:
            pass

def main():
    rclpy.init()
    node = TfToPose()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

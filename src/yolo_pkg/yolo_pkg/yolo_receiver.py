import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import socket
import json
import threading

class YOLOReceiver(Node):
    def __init__(self):
        super().__init__('yolo_receiver')
        
        # Parameters
        self.declare_parameter('udp_port', 5005)
        self.declare_parameter('udp_ip', '127.0.0.1')
        
        udp_port = self.get_parameter('udp_port').get_parameter_value().integer_value
        udp_ip = self.get_parameter('udp_ip').get_parameter_value().string_value
        
        # Publisher
        self.publisher_ = self.create_publisher(String, '/yolo/detections', 10)
        
        # Socket Setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((udp_ip, udp_port))
            self.get_logger().info(f'Listening for YOLO detections on {udp_ip}:{udp_port}')
        except Exception as e:
            self.get_logger().error(f'Could not bind to {udp_ip}:{udp_port}: {e}')
            return

        # Start listening thread
        self.running = True
        self.thread = threading.Thread(target=self.receive_loop)
        self.thread.start()

    def receive_loop(self):
        while self.running:
            try:
                # Set timeout so it doesn't block forever on shutdown
                self.sock.settimeout(1.0)
                data, addr = self.sock.recvfrom(65535) # Max UDP size
                
                # Decode JSON
                msg_content = data.decode('utf-8')
                
                # Create ROS Message
                msg = String()
                msg.data = msg_content
                self.publisher_.publish(msg)
                
                # Log the summary
                detections = json.loads(msg_content)
                if len(detections) > 0:
                    labels = [d['label'] for d in detections]
                    self.get_logger().info(f'Received: {", ".join(labels)}')
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.get_logger().error(f'UDP Error: {e}')

    def destroy_node(self):
        self.running = False
        self.thread.join()
        self.sock.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = YOLOReceiver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

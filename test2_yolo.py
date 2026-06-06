# Guardar en la Jetson como: ros_cam_stream.py
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time

# Variable global para almacenar el último frame recibido de ROS 2
latest_jpeg_bytes = None

class RosImageSubscriber(Node):
    def __init__(self):
        super().__init__('yolo_bridge_node')
        # Nos suscribimos al tópico comprimido que encontraste
        self.subscription = self.create_subscription(
            CompressedImage,
            '/image_raw/compressed',
            self.listener_callback,
            10)
        self.subscription  # Evitar alertas de la variable

    def listener_callback(self, msg):
        global latest_jpeg_bytes
        # msg.data ya contiene los bytes puros del JPEG estructurados por ROS 2
        latest_jpeg_bytes = bytes(msg.data)

class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith('.mjpg'):
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            while True:
                if latest_jpeg_bytes is not None:
                    try:
                        self.wfile.write(b'--jpgboundary\r\n')
                        self.send_header('Content-type', 'image/jpeg')
                        self.send_header('Content-length', str(len(latest_jpeg_bytes)))
                        self.end_headers()
                        self.wfile.write(latest_jpeg_bytes)
                        self.wfile.write(b'\r\n')
                    except (ConnectionResetError, BrokenPipeError):
                        break # El cliente (laptop) se desconectó
                time.sleep(0.03) # Transmisión estable a ~30 FPS

def start_http_server():
    server = HTTPServer(('0.0.0.0', 8089), CamHandler)
    server.serve_forever()

def main(args=None):
    rclpy.init(args=args)
    node = RosImageSubscriber()
    
    # Arrancamos el servidor web en un hilo secundario para que no congele a ROS 2
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    
    print("🚀 Puente ROS2 -> HTTP Activo.")
    print("Transmitiendo /image_raw/compressed en el puerto 8089...")
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

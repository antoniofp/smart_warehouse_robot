#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
import cv2
import numpy as np
import threading
import socket
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

latest_jpeg_bytes = None

class CamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global latest_jpeg_bytes
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
                        break
                time.sleep(0.20)
        else:
            self.send_response(404)
            self.end_headers()

class VisionTesterNode(Node):
    def __init__(self):
        super().__init__('vision_tester_node')

        self.cam_sub = self.create_subscription(
            CompressedImage,
            '/image_raw/compressed',
            self.camera_callback,
            1)

        server = HTTPServer(('0.0.0.0', 8089), CamHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print("[INFO] HTTP MJPEG Server running on port 8089")

        self.UDP_IP = "0.0.0.0"
        self.UDP_PORT = 5005
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
        self.sock.setblocking(False)
        self.udp_timer = self.create_timer(0.1, self.listen_yolo_udp)
        
        self.last_zone = None
        
        print("\n====================================================")
        print("  [VISION TESTER] Listo para recibir comandos UDP")
        print("====================================================\n")

    def camera_callback(self, msg):
        global latest_jpeg_bytes
        np_arr = np.frombuffer(msg.data, np.uint8)
        cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if cv_image is not None:
            ret, jpeg = cv2.imencode('.jpg', cv_image)
            if ret:
                latest_jpeg_bytes = jpeg.tobytes()

    def listen_yolo_udp(self):
        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                mensaje = data.decode('utf-8')
                print(f"[DEBUG UDP ENTRANTE]: {mensaje}") # RAW DUMP
                
                partes = mensaje.split(":")
                if len(partes) != 2:
                    continue
                clase_raw, cert_str = partes
                clase = clase_raw.strip().lower().replace(" ", "_").replace("-", "_")

                if "pedestrian" in clase:
                    if self.last_zone != "pedestrian":
                        self.last_zone = "pedestrian"
                        print(f"\n\033[96m\033[1m{'='*60}\n 🚶 🚶 🚶 PEDESTRIAN ZONE DETECTED 🚶 🚶 🚶\n{'='*60}\033[0m\n")

                elif "restricted" in clase:
                    if self.last_zone != "restricted":
                        self.last_zone = "restricted"
                        print(f"\n\033[91m\033[1m{'='*60}\n 🚨 🚨 🚨 RESTRICTED ZONE DETECTED 🚨 🚨 🚨\n{'='*60}\033[0m\n")

                elif "loading" in clase:
                    if self.last_zone != "loading":
                        self.last_zone = "loading"
                        print(f"\n\033[92m\033[1m{'='*60}\n 📦 📦 📦 LOADING ZONE DETECTED 📦 📦 📦\n{'='*60}\033[0m\n")

                elif "stop" in clase:
                    if self.last_zone != "stop":
                        self.last_zone = "stop"
                        print(f"\n\033[38;5;208m\033[1m{'='*60}\n 🛑 🛑 🛑 STOP FOR SAFETY DETECTED 🛑 🛑 🛑\n{'='*60}\033[0m\n")

                elif any(x in clase for x in ["robot", "agv"]):
                    if self.last_zone != "robots_only":
                        self.last_zone = "robots_only"
                        print(f"\n\033[93m\033[1m{'='*60}\n 🤖 🤖 🤖 ROBOTS-ONLY ZONE DETECTED 🤖 🤖 🤖\n{'='*60}\033[0m\n")

                elif "parking" in clase:
                    if self.last_zone != "parking":
                        self.last_zone = "parking"
                        print(f"\n\033[38;5;206m\033[1m{'='*60}\n 🅿️ 🅿️ 🅿️ FINAL PARKING ZONE REACHED 🅿️ 🅿️ 🅿️\n{'='*60}\033[0m\n")

        except BlockingIOError:
            pass
        except Exception as e:
            print(f"[ERROR UDP] Fallo al procesar el paquete: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = VisionTesterNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

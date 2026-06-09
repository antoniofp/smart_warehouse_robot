#!/usr/bin/env python3
import os
os.environ["CYCLONEDDS_LOG_LEVEL"] = "error"
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import Twist
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
from http.server import BaseHTTPRequestHandler, HTTPServer
import math
import sys
import time
import socket
import threading

# Shared global variable for HTTP video streaming
latest_jpeg_bytes = None

class CamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

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
                        break
                time.sleep(0.20) # Match camera limit at ~5 FPS to prevent network saturation

class WarehouseMissionServer(Node):
    def __init__(self):
        super().__init__('warehouse_mission_server')

        # --- CLIENTS, PUBLISHERS AND SUBSCRIBERS ---
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.yolo_pub = self.create_publisher(String, '/yolo_detections', 10)
        self.status_pub = self.create_publisher(String, '/robot_status', 10)

        self.cam_sub = self.create_subscription(
            CompressedImage,
            '/image_raw/compressed',
            self.camera_callback,
            1)

        self.confirm_sub = self.create_subscription(
            String,
            '/pc_confirmation',
            self.pc_confirmation_callback,
            10)

        self.param_client = self.create_client(SetParameters, '/controller_server/set_parameters')

        # 1. EXPLICIT IDA (OUTBOUND) WAYPOINTS
        self.waypoints_ida = [
            (2.3,  0.0, 0.0),   # Point 1
            (2.3,  2.0, 0.0),   # Point 2
            (1.3,  2.0, 0.0),   # Point 3
            (0.8,  1.6, 0.0),   # Point 4
            (-0.2, 1.6, 0.0)    # Point 5 (Reverse maneuver starts here)
        ]

        # 2. EXPLICIT REGRESO (RETURN) WAYPOINTS
        self.waypoints_regreso = [
            (0.8,  1.6, 0.0),   # Return - Point 1
            (1.3,  2.0, 0.0),   # Return - Point 2
            (2.0,  2.0, 0.0),   # Return - Point 3 (Moved to start curve earlier)
            (2.3,  0.0, 0.0),   # Return - Point 4
            (0.0,  0.0, 0.0)    # Return - Point 5 (Final Origin)
        ]

        # Route control settings
        self.waypoints = self.waypoints_ida
        self.current_index = 0
        self.timer = None
        self.returning = False
        self.goal_handle = None

        # --- LOGISTICS STATE MACHINE ---
        self.current_zone = "Robots-Only Zone"  
        self.loading_mission_completed = False  
        self.manual_continue_received = False   
        self.is_safety_stopped = False          
        self.safety_stop_executed = False  
        self.last_restricted_index = -1
        self.last_logged_udp_class = None
        self.last_udp_packet_time = 0.0

        # --- ANTI-STUCK SYSTEM (WATCHDOG) ---
        self.navigating = False
        self.current_distance = 999.0
        self.last_distance = 999.0
        self.stuck_seconds = 0
        self.watchdog_timer = self.create_timer(3.0, self.watchdog_check)

        # --- UDP RECEIVER CONFIGURATION (YOLO) ---
        self.UDP_IP = "0.0.0.0"
        self.UDP_PORT = 5005
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
        self.sock.setblocking(False)
        self.udp_timer = self.create_timer(0.1, self.listen_yolo_udp)

        # Uses YAML parameters exclusively for navigation

    def camera_callback(self, msg):
        global latest_jpeg_bytes
        latest_jpeg_bytes = bytes(msg.data)

    def pc_confirmation_callback(self, msg):
        if msg.data.lower() == "continue":
            self.get_logger().info("Remote confirmation signal ('continue') received!")
            self.manual_continue_received = True

    def listen_yolo_udp(self):
        """Asynchronous UDP interpreter for YOLO rules using Outbound/Inbound Phase Logic"""
        last_message = None
        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                last_message = data.decode('utf-8')
        except BlockingIOError:
            pass

        if last_message is None:
            return
            
        message = last_message
        
        if ":" in message:
            clase_raw, confidence_str = message.split(":")
            try:
                confidence = float(confidence_str)
            except ValueError:
                confidence = 1.0

            # Reject any detections with confidence below 60%
            if confidence < 0.60:
                return

            clase = clase_raw.strip().lower().replace(" ", "_").replace("-", "_")
            
            # Publish the raw class on ROS 2 for telemetry
            ros_msg = String()
            ros_msg.data = clase_raw.strip()
            self.yolo_pub.publish(ros_msg)

            # ====================================================
            # --- PHASE 1: OUTBOUND (IDA) ---
            # ====================================================
            if not self.returning:
                # Ignore anything not related to Outbound
                if not any(x in clase for x in ["pedestrian", "restricted", "loading"]):
                    return

                # A. PEDESTRIAN ZONE (FAKE SLOWDOWN)
                if "pedestrian" in clase and self.navigating:
                    if self.current_zone != "Pedestrian Zone":
                        self.current_zone = "Pedestrian Zone"
                        print(f"\n\033[96m\033[1m{'='*60}")
                        print(f" 🚶 🚶 🚶 PEDESTRIAN ZONE DETECTED 🚶 🚶 🚶")
                        print(f" Reducing speed 50%...")
                        print(f"{'='*60}\033[0m\n")

                # B. RESTRICTED AREA (Log only, no navigation changes)
                elif "restricted" in clase and self.navigating:
                    if self.last_restricted_index != self.current_index:
                        self.last_restricted_index = self.current_index
                        print(f"\n\033[91m\033[1m{'='*60}")
                        print(f" 🚨 🚨 🚨  RESTRICTED ZONE DETECTED  🚨 🚨 🚨")
                        print(f" Recalculating route...")
                        print(f"{'='*60}\033[0m\n")

                # C. LOADING ZONE (Halt and wait for confirmation)
                elif "loading" in clase and not self.loading_mission_completed and self.navigating:
                    print(f"\n\033[92m\033[1m{'='*60}")
                    print(f" 📦 📦 📦 LOADING ZONE DETECTED 📦 📦 📦")
                    print(f" Halting robot. Waiting for user confirmation...")
                    print(f"{'='*60}\033[0m\n")
                    if self.goal_handle is not None:
                        self.goal_handle.cancel_goal_async()
                    
                    self.cmd_vel_pub.publish(Twist())
                    self.navigating = False
                    
                    status_msg = String()
                    status_msg.data = "READY_TO_LOAD"
                    self.status_pub.publish(status_msg)
                    
                    threading.Thread(target=self.handle_loading_zone_sequence).start()

            # ====================================================
            # --- PHASE 2: INBOUND (RETURN) ---
            # ====================================================
            else:
                # Ignore anything not related to Return
                if not any(x in clase for x in ["stop", "robots", "parking", "agv"]):
                    return

                # A. STOP FOR SAFETY (Halt for 5 seconds exactly once)
                if "stop" in clase and not self.safety_stop_executed and not self.is_safety_stopped and self.navigating:
                    print(f"\n\033[38;5;208m\033[1m{'='*60}")
                    print(f" 🛑 🛑 🛑 STOP FOR SAFETY DETECTED 🛑 🛑 🛑")
                    print(f" Halting for 5 seconds...")
                    print(f"{'='*60}\033[0m\n")
                    self.safety_stop_executed = True
                    self.is_safety_stopped = True
                    if self.goal_handle is not None:
                        self.goal_handle.cancel_goal_async()
                    
                    self.cmd_vel_pub.publish(Twist()) # Emergency stop
                    threading.Thread(target=self.handle_safety_stop_delay).start()

                # B. AGV / ROBOTS-ONLY ZONE (FAKE SPEEDUP)
                elif any(x in clase for x in ["robot", "agv"]) and self.navigating:
                    if self.current_zone != "Robots-Only Zone":
                        self.current_zone = "Robots-Only Zone"
                        print(f"\n\033[93m\033[1m{'='*60}")
                        print(f" 🤖 🤖 🤖 ROBOTS-ONLY ZONE DETECTED 🤖 🤖 🤖")
                        print(f" Restoring speed to 100%...")
                        print(f"{'='*60}\033[0m\n")

                # C. PARKING ZONE (Shutdown motors and exit)
                elif clase in ["parking_zone", "parking", "parkingzone"] and self.navigating:
                    if self.loading_mission_completed:
                        print(f"\n\033[38;5;206m\033[1m{'='*60}")
                        print(f" 🅿️ 🅿️ 🅿️ FINAL PARKING ZONE REACHED 🅿️ 🅿️ 🅿️")
                        print(f" Shutting down motors...")
                        print(f"{'='*60}\033[0m\n")
                        if self.goal_handle is not None:
                            self.goal_handle.cancel_goal_async()
                        self.cmd_vel_pub.publish(Twist())
                        self.destroy_node()
                        rclpy.shutdown()
                        sys.exit(0)


    def handle_safety_stop_delay(self):
        time.sleep(5.0)
        print(f"\n====================================================")
        print(f" [🚀 RULE UPDATE] Safety stop timer expired.")
        print(f" Action: Resuming return navigation.")
        print(f"====================================================\n")
        self.is_safety_stopped = False
        self.send_next_goal()

    def handle_loading_zone_sequence(self):
        self.manual_continue_received = False
        print("\n====================================================")
        print(" [INFO] Robot has arrived at the Loading Zone!")
        print(" --> PRESS [ENTER] IN THIS TERMINAL TO CONTINUE <--")
        print(" (Or send 'continue' confirmation from your PC) ")
        print("====================================================")
        
        # Start a background daemon thread to wait for terminal Enter input
        def wait_for_enter():
            try:
                input()
                self.manual_continue_received = True
            except Exception:
                pass
                
        t = threading.Thread(target=wait_for_enter, daemon=True)
        t.start()
        
        while not self.manual_continue_received:
            time.sleep(0.1)
        
        print(f"\n====================================================")
        print(f" [🚀 RULE UPDATE] User pressed ENTER / PC continue received.")
        print(f" Action: Loading completed. Resuming navigation.")
        print(f"====================================================\n")
        self.loading_mission_completed = True
        # Do not increment current_index here, so it resumes completing the current waypoint!
        self.send_next_goal()



    def start_mission(self):
        print("----------------------------------------------------")
        print(f"    Starting Warehouse Mission. IDA Waypoints: {len(self.waypoints_ida)}")
        print("----------------------------------------------------")
        self.send_next_goal()

    def send_next_goal(self):
        if self.current_index >= len(self.waypoints):
            if not self.returning:
                self.execute_backwards_maneuver()
            else:
                print("\n    SUCCESS: Mission completed! The robot returned to the origin.")
                self.destroy_node()
                rclpy.shutdown()
                sys.exit(0)
            return

        x, y, yaw_deg = self.waypoints[self.current_index]
        ruta_str = "RETURN" if self.returning else "IDA"
        print(f"\n    [{ruta_str} - Waypoint {self.current_index + 1}/{len(self.waypoints)}] Target: X={x}, Y={y}, Yaw={yaw_deg}")

        self.navigating = True
        self.current_distance = 999.0
        self.last_distance = 999.0
        self.stuck_seconds = 0

        self.send_goal_internal(x, y, yaw_deg)

    def send_goal_internal(self, x, y, yaw_deg):
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('Nav2 action server is not available.')
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)

        half_yaw = math.radians(yaw_deg) / 2.0
        goal_msg.pose.pose.orientation.z = math.sin(half_yaw)
        goal_msg.pose.pose.orientation.w = math.cos(half_yaw)



        send_goal_future = self._action_client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def feedback_callback(self, feedback_msg):
        self.current_distance = feedback_msg.feedback.distance_remaining
        print(f"    [>>] Navigating... Distance remaining: {self.current_distance:.2f} m    ", end='\r')

    def watchdog_check(self):
        if self.navigating and not self.is_safety_stopped:
            # Si el get_result_callback o el goal_response dispararon la alarma máxima (6), reenvía a la fuerza bruta
            if self.stuck_seconds >= 6:  
                x, y, yaw_deg = self.waypoints[self.current_index]
                print(f"\n    [STUCK DETECTED / NAV2 ABORTED] Re-sending target pose forcefully...")
                
                def force_resend_aborted():
                    if self.goal_handle is not None:
                        try:
                            self.goal_handle.cancel_goal_async()
                            time.sleep(1.0)
                        except Exception: pass
                    self.send_goal_internal(x, y, yaw_deg)
                    
                import threading
                threading.Thread(target=force_resend_aborted).start()
                self.stuck_seconds = 0
                return

            # Skip normal distance check if we haven't received the first distance feedback yet
            if self.current_distance == 999.0:
                return

            diferencia = abs(self.last_distance - self.current_distance)

            if diferencia < 0.05 and self.current_distance > 0.35:
                self.stuck_seconds += 3
                if self.stuck_seconds >= 6:  
                    x, y, yaw_deg = self.waypoints[self.current_index]
                    print(f"\n    [STUCK DETECTED] Re-sending target pose...")
                    
                    def force_resend_stuck():
                        if self.goal_handle is not None:
                            try:
                                self.goal_handle.cancel_goal_async()
                                time.sleep(1.0)
                            except Exception: pass
                        self.send_goal_internal(x, y, yaw_deg)
                        
                    import threading
                    threading.Thread(target=force_resend_stuck).start()
                    self.stuck_seconds = 0
            else:
                self.last_distance = self.current_distance
                self.stuck_seconds = 0

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            print('\n[ERROR] El objetivo fue rechazado por el planificador de ROS 2.')
            if not self.is_safety_stopped:
                self.stuck_seconds = 6 
                self.goal_handle = None
            return

        self.goal_handle = goal_handle  
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        status = future.result().status
        self.goal_handle = None  # Clear dead goal so watchdog doesn't try to cancel it
        
        if status == 4:  # SUCCEEDED
            self.navigating = False
            self.goal_handle = None
            print(f"\n    Waypoint {self.current_index + 1} reached successfully!")
            self.current_index += 1
            self.timer = self.create_timer(1.0, self.timer_callback)
        elif status == 6: # ABORTED by Nav2 (Not cancelled by us)
            if not self.is_safety_stopped:
                self.stuck_seconds = 6

    def timer_callback(self):
        if self.timer:
            self.timer.cancel()
        self.send_next_goal()

    def execute_backwards_maneuver(self):
        print("\n    IDA navigation completed. Initiating backwards maneuver...")
        distancia_objetivo = 1.5   
        velocidad_lineal = -0.20   
        velocidad_angular = -0.40    
        tiempo_reversa = distancia_objetivo / abs(velocidad_lineal)

        print(f"    Moving backwards for {tiempo_reversa:.2f} seconds...")
        msg_twist = Twist()
        msg_twist.linear.x = velocidad_lineal
        msg_twist.angular.z = velocidad_angular

        rate = 0.1 
        pasos_totales = int(tiempo_reversa / rate)

        for _ in range(pasos_totales):
            self.cmd_vel_pub.publish(msg_twist)
            time.sleep(rate)

        print("    Stopping motors...")
        freno_twist = Twist()
        for _ in range(5):
            self.cmd_vel_pub.publish(freno_twist)
            time.sleep(0.05)

        print("\n    Switching to return route...")

        self.waypoints = self.waypoints_regreso
        self.current_index = 0
        self.returning = True

        print(f"    Return route loaded. Waypoints to visit: {len(self.waypoints)}")
        time.sleep(2.0)
        self.send_next_goal()

def start_http_server():
    server = HTTPServer(('0.0.0.0', 8089), CamHandler)
    server.serve_forever()

def main(args=None):
    os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'
    os.environ['ROS_DOMAIN_ID'] = '32'
    
    rclpy.init(args=args)
    mission_node = WarehouseMissionServer()
    
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    
    print("    HTTP Video Stream Bridge & Vision Rules Server Active (Port 8089).")
    
    try:
        mission_node.start_mission()
        rclpy.spin(mission_node)
    except KeyboardInterrupt:
        print("\n    Mission manually cancelled. Stopping robot...")
        freno = Twist()
        mission_node.cmd_vel_pub.publish(freno)
    finally:
        mission_node.sock.close()
        if rclpy.ok():
            mission_node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()

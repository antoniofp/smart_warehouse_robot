#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import Twist
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import String
from http.server import BaseHTTPRequestHandler, HTTPServer
import math
import sys
import time
import os
import socket
import threading

# Variable global compartida para el streaming de video HTTP
latest_jpeg_bytes = None

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
                        break
                time.sleep(0.03) # Streaming fluido a ~30 FPS

class WarehouseMissionServer(Node):
    def __init__(self):
        super().__init__('warehouse_mission_server')

        # --- CLIENTES, PUBLICADORES Y SUSCRIPTORES ---
        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.yolo_pub = self.create_publisher(String, '/yolo_detections', 10)
        self.status_pub = self.create_publisher(String, '/robot_status', 10)

        self.cam_sub = self.create_subscription(
            CompressedImage,
            '/image_raw/compressed',
            self.camera_callback,
            10)

        self.confirm_sub = self.create_subscription(
            String,
            '/pc_confirmation',
            self.pc_confirmation_callback,
            10)

        # 1. LISTA EXPLÍCITA DE WAYPOINTS DE IDA
        self.waypoints_ida = [
            (2.3,  0.0, 0.0),   # Punto 1
            (2.3,  2.0, 0.0),   # Punto 2
            (1.3,  2.0, 0.0),   # Punto 3
            (0.8,  1.6, 0.0),   # Punto 4
            (-0.2, 1.6, 0.0)    # Punto 5 (Aquí entra la reversa)
        ]

        # 2. LISTA EXPLÍCITA DE WAYPOINTS DE REGRESO (Origen al final)
        self.waypoints_regreso = [
            (0.8,  1.6, 0.0),   # Regreso - Punto 1
            (1.3,  2.0, 0.0),   # Regreso - Punto 2
            (2.3,  2.0, 0.0),   # Regreso - Punto 3
            (2.3,  0.0, 0.0),   # Regreso - Punto 4
            (0.0,  0.0, 0.0)    # Regreso - Punto 5 (Origen Final)
        ]

        # Configuración de control de ruta
        self.waypoints = self.waypoints_ida
        self.current_index = 0
        self.timer = None
        self.returning = False
        self.goal_handle = None

        # --- MÁQUINA DE ESTADOS LOGÍSTICA ---
        self.current_zone = "Robots-Only Zone"  
        self.loading_mission_completed = False  
        self.manual_continue_received = False   
        self.is_safety_stopped = False          

        # --- SISTEMA ANTI-ATASCOS (WATCHDOG) ---
        self.navigating = False
        self.current_distance = 999.0
        self.last_distance = 999.0
        self.stuck_seconds = 0
        self.watchdog_timer = self.create_timer(3.0, self.watchdog_check)

        # --- CONFIGURACIÓN RECEPTOR UDP (YOLO) ---
        self.UDP_IP = "0.0.0.0"
        self.UDP_PORT = 5005
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
        self.sock.setblocking(False)
        self.udp_timer = self.create_timer(0.1, self.listen_yolo_udp)

        # Interceptación del flujo de velocidad de Nav2 para aplicar reducciones dinámicas
        self.cmd_vel_sub = self.create_subscription(Twist, '/cmd_vel_nav2_raw', self.cmd_vel_filter_callback, 10)

    def camera_callback(self, msg):
        global latest_jpeg_bytes
        latest_jpeg_bytes = bytes(msg.data)

    def pc_confirmation_callback(self, msg):
        if msg.data.lower() == "continue":
            self.get_logger().info("¡Se recibió la señal remota para continuar!")
            self.manual_continue_received = True

    def listen_yolo_udp(self):
        """Intérprete asíncrono de las 6 reglas basadas en visión"""
        try:
            data, addr = self.sock.recvfrom(1024)
            mensaje_recibido = data.decode('utf-8')
            
            if ":" in mensaje_recibido:
                clase, certeza = mensaje_recibido.split(":")
                clase = clase.strip()
                
                ros_msg = String()
                ros_msg.data = clase
                self.yolo_pub.publish(ros_msg)

                # 1. RESTRICTED AREA
                if clase == "Restricted Area" and self.navigating:
                    print(f"\n[⚠️ REGLA: Restricted Area] Evitando zona. Modificando trayectoria...")
                    if self.goal_handle is not None:
                        self.goal_handle.cancel_goal_async()
                    self.stuck_seconds = 0
                    self.current_index += 1  # Salta el punto actual para explorar el resto
                    self.send_next_goal()

                # 2. PEDESTRIAN ZONE
                elif clase == "Pedestrian Zone":
                    if self.current_zone != "Pedestrian Zone":
                        print(f"\n[🚶 REGLA: Pedestrian Zone] Operadores en área. Velocidad reducida al 50%.")
                        self.current_zone = "Pedestrian Zone"

                # 3. ROBOTS-ONLY ZONE
                elif clase == "Robots-Only Zone":
                    if self.current_zone != "Robots-Only Zone":
                        print(f"\n[🤖 REGLA: Robots-Only Zone] Zona segura. Restableciendo velocidad normal.")
                        self.current_zone = "Robots-Only Zone"

                # 4. STOP FOR SAFETY
                elif clase == "Stop for Safety" and not self.is_safety_stopped and self.navigating:
                    print(f"\n[🛑 REGLA: Stop for Safety] Obstáculo detectado. Frenando por 5 segundos...")
                    self.is_safety_stopped = True
                    if self.goal_handle is not None:
                        self.goal_handle.cancel_goal_async()
                    
                    self.cmd_vel_pub.publish(Twist()) # Freno instantáneo
                    threading.Thread(target=self.handle_safety_stop_delay).start()

                # 5. LOADING ZONE
                elif clase == "Loading Zone" and not self.loading_mission_completed and self.navigating:
                    print(f"\n[📦 REGLA: Loading Zone] Robot alineado y en posición de carga. Estacionando...")
                    if self.goal_handle is not None:
                        self.goal_handle.cancel_goal_async()
                    
                    self.cmd_vel_pub.publish(Twist())
                    self.navigating = False
                    
                    status_msg = String()
                    status_msg.data = "READY_TO_LOAD"
                    self.status_pub.publish(status_msg)
                    
                    threading.Thread(target=self.handle_loading_zone_sequence).start()

                # 6. PARKING ZONE
                elif clase == "Parking Zone" and self.navigating:
                    if self.loading_mission_completed:
                        print(f"\n[🅿️ REGLA: Parking Zone] Estacionamiento final alcanzado con éxito. Apagando motores.")
                        if self.goal_handle is not None:
                            self.goal_handle.cancel_goal_async()
                        self.cmd_vel_pub.publish(Twist())
                        self.destroy_node()
                        rclpy.shutdown()
                        sys.exit(0)
                    else:
                        print(f"\n[ℹ️ INFO: Parking Zone] Pasando de largo (Carga pendiente).")

        except BlockingIOError:
            pass

    def handle_safety_stop_delay(self):
        time.sleep(5.0)
        print("    -> Tiempo de seguridad cumplido. Reanudando marcha...")
        self.is_safety_stopped = False
        self.send_next_goal()

    def handle_loading_zone_sequence(self):
        self.manual_continue_received = False
        print("    [ESPERA] Esperando confirmación remota ('continue') desde la PC...")
        while not self.manual_continue_received:
            time.sleep(0.5)
        
        print("    -> Carga lista. Avanzando directo al punto de Parking (Siguiente Waypoint)...")
        self.loading_mission_completed = True
        self.current_index += 1  
        self.send_next_goal()

    def cmd_vel_filter_callback(self, msg):
        """Modulador dinámico de velocidad en base a las zonas de visión"""
        twist_modificado = Twist()
        twist_modificado.angular.z = msg.angular.z
        
        if self.current_zone == "Pedestrian Zone":
            twist_modificado.linear.x = msg.linear.x * 0.5  # Velocidad dividida a la mitad
        else:
            twist_modificado.linear.x = msg.linear.x
            
        if not self.is_safety_stopped and self.navigating:
            self.cmd_vel_pub.publish(twist_modificado)

    def start_mission(self):
        print("----------------------------------------------------")
        print(f"    Iniciando misión de almacén. Puntos de IDA: {len(self.waypoints_ida)}")
        print("----------------------------------------------------")
        self.send_next_goal()

    def send_next_goal(self):
        if self.current_index >= len(self.waypoints):
            if not self.returning:
                self.execute_backwards_maneuver()
            else:
                print("\n    ¡MISIÓN COMPLETADA CON ÉXITO! El robot volvió al origen original.")
                self.destroy_node()
                rclpy.shutdown()
                sys.exit(0)
            return

        x, y, yaw_deg = self.waypoints[self.current_index]
        ruta_str = "REGRESO" if self.returning else "IDA"
        print(f"\n    [{ruta_str} - Punto {self.current_index + 1}/{len(self.waypoints)}] Objetivo principal: X={x}, Y={y}, Yaw={yaw_deg}")

        self.navigating = True
        self.current_distance = 999.0
        self.last_distance = 999.0
        self.stuck_seconds = 0

        self.send_goal_internal(x, y, yaw_deg)

    def send_goal_internal(self, x, y, yaw_deg):
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error('El servidor de Nav2 no está disponible.')
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)

        half_yaw = math.radians(yaw_deg) / 2.0
        goal_msg.pose.pose.orientation.z = math.sin(half_yaw)
        goal_msg.pose.pose.orientation.w = math.cos(half_yaw)

        print(f"    [ENVIANDO] Inyectando coordenadas a Nav2: X={x}, Y={y}...")

        send_goal_future = self._action_client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def feedback_callback(self, feedback_msg):
        self.current_distance = feedback_msg.feedback.distance_remaining
        print(f"    [>>] Moviendo... Distancia al destino: {self.current_distance:.2f} m    ", end='\r')

    def watchdog_check(self):
        if self.navigating and not self.is_safety_stopped:
            diferencia = abs(self.last_distance - self.current_distance)

            if self.current_distance == 999.0 or diferencia < 0.05:
                self.stuck_seconds += 3
                if self.stuck_seconds >= 6:  
                    x, y, yaw_deg = self.waypoints[self.current_index]
                    print(f"\n    [ATASCO DETECTADO] Re-enviando de forma continua e instantánea.")
                    
                    if self.goal_handle is not None:
                        self.goal_handle.cancel_goal_async()
                    
                    self.send_goal_internal(x, y, yaw_deg)
                    self.stuck_seconds = 0
            else:
                self.last_distance = self.current_distance
                self.stuck_seconds = 0

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.stuck_seconds = 6 
            return

        self.goal_handle = goal_handle  
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        status = future.result().status
        if status == 4:  # SUCCEEDED
            self.navigating = False
            self.goal_handle = None
            print(f"\n    Punto {self.current_index + 1} alcanzado con éxito!")
            self.current_index += 1
            self.timer = self.create_timer(1.0, self.timer_callback)
        else:
            if not self.is_safety_stopped:
                self.stuck_seconds = 6

    def timer_callback(self):
        if self.timer:
            self.timer.cancel()
        self.send_next_goal()

    def execute_backwards_maneuver(self):
        print("\n    Mapeo de ida listo. Iniciando maniobra de reversa...")
        distancia_objetivo = 1.5   
        velocidad_lineal = -0.20   
        velocidad_angular = -0.40    
        tiempo_reversa = distancia_objetivo / abs(velocidad_lineal)

        print(f"    Moviendo en reversa durante {tiempo_reversa:.2f} segundos...")
        msg_twist = Twist()
        msg_twist.linear.x = velocidad_lineal
        msg_twist.angular.z = velocidad_angular

        rate = 0.1 
        pasos_totales = int(tiempo_reversa / rate)

        for _ in range(pasos_totales):
            self.cmd_vel_pub.publish(msg_twist)
            time.sleep(rate)

        print("    Deteniendo motores...")
        freno_twist = Twist()
        for _ in range(5):
            self.cmd_vel_pub.publish(freno_twist)
            time.sleep(0.05)

        print("\n    Cambiando a la ruta explícita de regreso...")

        self.waypoints = self.waypoints_regreso
        self.current_index = 0
        self.returning = True

        print(f"    Ruta de regreso cargada. Puntos totales a visitar: {len(self.waypoints)}")
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
    
    print("    Puente de Streaming HTTP y Servidor de Reglas Inteligentes Activo (Puerto 8089).")
    
    try:
        mission_node.start_mission()
        rclpy.spin(mission_node)
    except KeyboardInterrupt:
        print("\n    Misión cancelada manualmente. Deteniendo el carro...")
        freno = Twist()
        mission_node.cmd_vel_pub.publish(freno)
    finally:
        mission_node.sock.close()
        if rclpy.ok():
            mission_node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()

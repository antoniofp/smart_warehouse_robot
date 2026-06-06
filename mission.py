#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import Twist
import math
import sys
import time
import os

class WarehouseMissionServer(Node):
    def __init__(self):
        super().__init__('warehouse_mission_server')

        self._action_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # 1. LISTA EXPLÍCITA DE IDA
        self.waypoints_ida = [
            (2.3,  0.0, 0.0),   # Punto 1
            (2.3,  2.0, 0.0),   # Punto 2
            (1.3,  2.0, 0.0),   # Punto 3
            (0.8,  1.6, 0.0),   # Punto 4
            (-0.2, 1.6, 0.0)    # Punto 5 (Aquí entra la reversa)
        ]

        # 2. LISTA EXPLÍCITA DE REGRESO CORREGIDA
        # El origen (0.0, 0.0, 0.0) ahora es el último destino de la misión
        self.waypoints_regreso = [
            (0.8,  1.6, 0.0),   # Regreso - Punto 1
            (1.3,  2.0, 0.0),   # Regreso - Punto 2
            (2.3,  2.0, 0.0),   # Regreso - Punto 3
            (2.3,  0.0, 0.0),   # Regreso - Punto 4
            (0.0,  0.0, 0.0)    # Regreso - Punto 5 (Punto Final)
        ]

        # Apuntamos inicialmente a la ruta de ida
        self.waypoints = self.waypoints_ida
        self.current_index = 0
        self.timer = None
        self.returning = False
        self.goal_handle = None  # Almacena el handle activo para poder cancelarlo si se traba

        # --- SISTEMA ANTI-ATASCOS (WATCHDOG) ---
        self.navigating = False
        self.current_distance = 999.0
        self.last_distance = 999.0
        self.stuck_seconds = 0
        self.watchdog_timer = self.create_timer(3.0, self.watchdog_check)

    def start_mission(self):
        print("----------------------------------------------------")
        print(f"    Iniciando misión de almacén. Puntos de IDA: {len(self.waypoints_ida)}")
        print("----------------------------------------------------")
        self.send_next_goal()

    def send_next_goal(self):
        if self.current_index >= len(self.waypoints):
            if not self.returning:
                # Al acabar la ida, ejecutamos la maniobra física de reversa
                self.execute_backwards_maneuver()
            else:
                # Al acabar la lista de regreso (alcanzar el 0,0,0), la misión termina
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
        if self.navigating:
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

        print("\n    Cambiando a la ruta explícita de regreso ordenada al revés...")

        # Activamos la lista fija de regreso con el (0,0,0) al final
        self.waypoints = self.waypoints_regreso
        self.current_index = 0
        self.returning = True

        print(f"    Ruta de regreso cargada. Puntos totales a visitar: {len(self.waypoints)}")
        time.sleep(2.0)
        self.send_next_goal()

def main(args=None):
    os.environ['RMW_IMPLEMENTATION'] = 'rmw_cyclonedds_cpp'
    os.environ['ROS_DOMAIN_ID'] = '32'
    
    rclpy.init(args=args)
    mission_node = WarehouseMissionServer()
    
    try:
        mission_node.start_mission()
        rclpy.spin(mission_node)
    except KeyboardInterrupt:
        print("\n    Misión cancelada manualmente. Deteniendo el carro...")
        freno = Twist()
        mission_node.cmd_vel_pub.publish(freno)
    finally:
        if rclpy.ok():
            mission_node.destroy_node()
            rclpy.shutdown()

if __name__ == '__main__':
    main()

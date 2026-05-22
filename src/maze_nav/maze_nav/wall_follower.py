import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid, Path, Odometry  # <-- Cambiado: Se añadió Odometry
from geometry_msgs.msg import Twist
import math
import numpy as np
import time

class PIDController:
    """Controlador PID con Anti-Windup para el volante"""
    def __init__(self, kp, ki, kd, max_output, min_output):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.min_output = min_output
        
        self.error_anterior = 0.0
        self.integral = 0.0
        self.tiempo_anterior = time.time()

    def calcular(self, error):
        tiempo_actual = time.time()
        dt = tiempo_actual - self.tiempo_anterior
        if dt <= 0.0:
            dt = 0.01  # Evitar división por cero
            
        # Proporcional
        P = self.kp * error
        
        # Integral con Anti-Windup
        self.integral += error * dt
        I = self.ki * self.integral
        
        # Derivativo
        derivada = (error - self.error_anterior) / dt
        D = self.kd * derivada
        
        # Salida total
        salida = P + I + D
        
        # Saturación (Límites físicos del volante)
        if salida > self.max_output:
            salida = self.max_output
            self.integral -= error * dt # Deshacer integración
        elif salida < self.min_output:
            salida = self.min_output
            self.integral -= error * dt # Deshacer integración
            
        self.error_anterior = error
        self.tiempo_anterior = tiempo_actual
        
        return salida

class PathFollower(Node):
    def __init__(self):
        super().__init__('pid_path_follower')
        
        self.L = 0.3                
        self.MAX_STEER = math.radians(30)
        self.MAX_V = 0.50            
        self.MIN_V = -0.25         
        
        self.LOOKAHEAD_DIST = 0.28   
        self.STOP_DIST = 0.15            
        
        # 🎯 INSTANCIA DEL PID (Ajusta estos valores si oscila o es lento)
        self.pid_volante = PIDController(
            kp=1.5, 
            ki=0.01, 
            kd=0.2, 
            max_output=self.MAX_STEER, 
            min_output=-self.MAX_STEER
        )

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        # 💡 CAMBIO CRÍTICO: Suscribirse a /odom en lugar de /pose
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.pose_callback, 10)
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.path_sub = self.create_subscription(Path, '/plan', self.path_callback, 10)

        self.x, self.y, self.theta = None, None, None
        self.current_path = []
        self.goal_reached = True    
        self.map_data = None
        self.map_res = 0.05
        self.map_origin_x = 0.0
        self.map_origin_y = 0.0
        self.map_width = 0
        
        self.last_direction = 1.0  
        
        self.timer = self.create_timer(0.05, self.control_loop)
        self.log_counter = 0 
        self.get_logger().info("🚀 [FOLLOWER PID] Inicializado y escuchando a /odom.")

    def pose_callback(self, msg):
        # 💡 CAMBIO CRÍTICO: Leer de pose.pose.position para Odometry
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.theta = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))

    def map_callback(self, msg):
        self.map_res = msg.info.resolution
        self.map_origin_x = msg.info.origin.position.x
        self.map_origin_y = msg.info.origin.position.y
        self.map_width = msg.info.width
        self.map_data = np.array(msg.data)

    def path_callback(self, msg):
        if not msg.poses:
            return
        self.current_path = msg.poses
        self.goal_reached = False

    def is_obstacle_ahead(self, move_direction):
        if self.map_data is None or self.x is None:
            return False
            
        check_distances = [0.1, 0.15, 0.2] 
        check_theta = self.theta if move_direction >= 0 else self.theta + math.pi
        
        for dist in check_distances:
            check_x = self.x + dist * math.cos(check_theta)
            check_y = self.y + dist * math.sin(check_theta)
            grid_x = int((check_x - self.map_origin_x) / self.map_res)
            grid_y = int((check_y - self.map_origin_y) / self.map_res)
            index = grid_y * self.map_width + grid_x
            
            if 0 <= index < len(self.map_data):
                if self.map_data[index] > 65: 
                    return True
        return False

    def get_lookahead_point(self):
        if not self.current_path:
            return self.x, self.y

        min_dist = float('inf')
        closest_idx = 0
        for i, p in enumerate(self.current_path):
            dist = math.hypot(p.pose.position.x - self.x, p.pose.position.y - self.y)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i
                
        self.current_path = self.current_path[closest_idx:]

        for i in range(len(self.current_path)):
            px = self.current_path[i].pose.position.x
            py = self.current_path[i].pose.position.y
            dist = math.hypot(px - self.x, py - self.y)
            if dist >= self.LOOKAHEAD_DIST:
                return px, py
                
        return self.current_path[-1].pose.position.x, self.current_path[-1].pose.position.y

    def control_loop(self):
        self.log_counter += 1
        if self.x is None or self.goal_reached or not self.current_path:
            return

        final_x = self.current_path[-1].pose.position.x
        final_y = self.current_path[-1].pose.position.y
        dist_to_final = math.hypot(final_x - self.x, final_y - self.y)

        if dist_to_final < self.STOP_DIST:
            self.stop_robot()
            self.goal_reached = True
            self.current_path = []
            return

        target_x, target_y = self.get_lookahead_point()
        dx = target_x - self.x
        dy = target_y - self.y
        target_theta = math.atan2(dy, dx)

        # Histéresis de marcha (mantenida igual)
        raw_error = target_theta - self.theta
        cos_error = math.cos(raw_error)
        
        if self.last_direction == 1.0:
            direction = -1.0 if cos_error < -0.25 else 1.0  
        else:
            direction = 1.0 if cos_error > 0.25 else -1.0   
        self.last_direction = direction

        if self.is_obstacle_ahead(direction):
            self.stop_robot()
            if self.log_counter % 10 == 0:
                self.get_logger().warning("🛑 [FOLLOWER] ¡OBSTÁCULO! Frenado preventivo.")
            return

        # Calcular el error de orientación respecto al punto objetivo
        theta_v = self.theta if direction == 1.0 else self.theta + math.pi
        e_theta = target_theta - theta_v
        e_theta = math.atan2(math.sin(e_theta), math.cos(e_theta)) # Normalizar entre -pi y pi

        # 💡 APLICAR PID PARA EL VOLANTE
        delta = self.pid_volante.calcular(e_theta)

        # 💡 CONTROL DINÁMICO DE VELOCIDAD
        # Reducir velocidad si el volante está muy girado (factor va de 1.0 en recta a 0.4 en curva máxima)
        factor_curva = max(0.4, 1.0 - (abs(delta) / self.MAX_STEER))
        
        # Velocidad base dependiendo de si vamos adelante o atrás
        vel_base = self.MAX_V if direction == 1.0 else abs(self.MIN_V)
        v = direction * vel_base * factor_curva

        # Freno suave al acercarse a la meta final
        if dist_to_final < 0.8:
            v *= max(0.4, dist_to_final)

        # Velocidad mínima para que no se quede estancado
        if abs(v) < 0.10 and not self.goal_reached:
            v = 0.10 * direction

        # Aplicar límites absolutos
        v = max(min(v, self.MAX_V), self.MIN_V)

        cmd = Twist()
        cmd.linear.x = float(v)
        cmd.angular.z = float(delta) 
        self.cmd_pub.publish(cmd)
        
        if self.log_counter % 20 == 0:
            marcha = "Adelante" if direction > 0 else "Reversa"
            self.get_logger().info(
                f"🎯 [FOLLOWER PID] {marcha} | Quedan: {dist_to_final:.2f}m | Vel: {v:.2f}m/s | Volante: {math.degrees(delta):.1f}°"
            )

    def stop_robot(self):
        cmd = Twist()
        cmd.linear.x = 0.0
        cmd.angular.z = 0.0
        self.cmd_pub.publish(cmd)

def main():
    rclpy.init()
    node = PathFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop_robot()
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

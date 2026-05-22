import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from nav2_msgs.action import NavigateToPose
from geometry_msgs.msg import PoseStamped, Twist
import time

class ExploreBridge(Node):
    def __init__(self):
        super().__init__('explore_bridge')
        
        # Usamos un grupo de ejecución reentrante para que los callbacks corran en paralelo
        self.cb_group = ReentrantCallbackGroup()
        
        self.goal_pub = self.create_publisher(
            PoseStamped, '/goal_pose', 10, callback_group=self.cb_group
        )
        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_callback, 10, callback_group=self.cb_group
        )
        
        self.robot_moving = False
        self.previous_state = False 
        
        self._action_server = ActionServer(
            self,
            NavigateToPose,
            'navigate_to_pose',
            self.execute_callback,
            callback_group=self.cb_group
        )
            
        self.get_logger().info("🌉 [BRIDGE] Puente Explore-Lite inicializado (Multihilo). Haciéndome pasar por Nav2...")

    def cmd_callback(self, msg):
        # Determinamos si el robot se está moviendo lineal o angularmente
        is_moving_now = (abs(msg.linear.x) > 0.01 or abs(msg.angular.z) > 0.01)
        
        # Log simplificado para evitar Spam masivo
        if is_moving_now and not self.previous_state:
            self.get_logger().info("⚙️ [BRIDGE] Robot detectado en MOVIMIENTO.")
        elif not is_moving_now and self.previous_state:
            self.get_logger().info("🛑 [BRIDGE] Robot detectado DETENIDO.")
            
        self.robot_moving = is_moving_now
        self.previous_state = is_moving_now

    def execute_callback(self, goal_handle):
        self.get_logger().info('📡 [BRIDGE] Explore_lite solicita viajar a una frontera. Redirigiendo a /goal_pose...')
        
        # Construir y publicar la meta para el planificador global
        pose_msg = PoseStamped()
        pose_msg.header = goal_handle.request.pose.header
        pose_msg.pose = goal_handle.request.pose.pose
        self.goal_pub.publish(pose_msg)
        
        self.get_logger().info('⏳ [BRIDGE] Meta enviada. Esperando dinámicamente a que el robot arranque...')
        
        # ESPERA DINÁMICA: Espera un máximo de 3.0 segundos a que los motores reporten movimiento
        start_timeout = time.time()
        while not self.robot_moving and (time.time() - start_timeout) < 3.0:
            time.sleep(0.1)
        
        # Si el robot se está moviendo, lo monitoreamos de cerca hasta que termine
        if self.robot_moving:
            self.get_logger().info('👀 [BRIDGE] ¡Robot en marcha! Monitoreando motores...')
            while self.robot_moving:
                time.sleep(0.1)
            self.get_logger().info('🏁 [BRIDGE] El robot llegó o se detuvo. Reportando ÉXITO a explore_lite.')
        else:
            self.get_logger().warning('⚠️ [BRIDGE] El robot no inició movimiento tras 3s. Forzando éxito para evitar bloqueos.')
        
        # Responder exitosamente a explore_lite para que calcule la siguiente frontera
        goal_handle.succeed()
        return NavigateToPose.Result()

def main():
    rclpy.init()
    node = ExploreBridge()
    
    # IMPORTANTE: Usamos MultiThreadedExecutor para que no se bloqueen los callbacks entre sí
    executor = MultiThreadedExecutor()
    try:
        rclpy.spin(node, executor=executor)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()

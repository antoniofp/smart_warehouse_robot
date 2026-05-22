import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid, Path, Odometry # 💡 CAMBIO: Se añadió Odometry
from geometry_msgs.msg import PoseStamped
import heapq
import math
import numpy as np

class GlobalPlanner(Node):
    def __init__(self):
        super().__init__('global_planner')
        
        # 👇 RADIO REDUCIDO PARA PASAR POR PASILLOS ESTRECHOS 👇
        self.INFLATION_RADIUS = 0.18 
        
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        # 💡 CAMBIO CRÍTICO: Escuchar /odom en lugar de /pose
        self.pose_sub = self.create_subscription(Odometry, '/odom', self.pose_callback, 10)
        self.goal_sub = self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        self.path_pub = self.create_publisher(Path, '/plan', 10)

        self.map_data = None
        self.inflated_map = None
        self.map_info = None
        self.start_x, self.start_y = None, None
        self.get_logger().info("🧠 [PLANNER] Inicializado y escuchando a /odom. Esperando meta en /goal_pose...")

    def pose_callback(self, msg):
        # 💡 CAMBIO CRÍTICO: Leer x e y desde pose.pose.position
        self.start_x = msg.pose.pose.position.x
        self.start_y = msg.pose.pose.position.y

    def map_callback(self, msg):
        if self.map_data is None:
            self.get_logger().info("🗺️ [PLANNER] Primer mapa recibido. Inflando...")
            
        self.map_info = msg.info
        grid = np.array(msg.data).reshape((msg.info.height, msg.info.width))
        self.map_data = grid
        self.inflate_obstacles()

    def inflate_obstacles(self):
        self.inflated_map = np.copy(self.map_data)
        inflation_cells = int(self.INFLATION_RADIUS / self.map_info.resolution)
        walls = np.argwhere(self.map_data > 50)
        
        for wy, wx in walls:
            y_min = max(0, wy - inflation_cells)
            y_max = min(self.map_info.height, wy + inflation_cells + 1)
            x_min = max(0, wx - inflation_cells)
            x_max = min(self.map_info.width, wx + inflation_cells + 1)
            self.inflated_map[y_min:y_max, x_min:x_max] = 100

    def world_to_grid(self, wx, wy):
        gx = int((wx - self.map_info.origin.position.x) / self.map_info.resolution)
        gy = int((wy - self.map_info.origin.position.y) / self.map_info.resolution)
        return gx, gy

    def grid_to_world(self, gx, gy):
        wx = (gx * self.map_info.resolution) + self.map_info.origin.position.x
        wy = (gy * self.map_info.resolution) + self.map_info.origin.position.y
        return wx, wy

    def find_nearest_free_cell(self, start_g, max_radius=15):
        for r in range(1, max_radius):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) == r:
                        nx, ny = start_g[0] + dx, start_g[1] + dy
                        if 0 <= nx < self.map_info.width and 0 <= ny < self.map_info.height:
                            if self.inflated_map[ny, nx] <= 50:
                                return (nx, ny)
        return None

    def goal_callback(self, msg):
        if self.inflated_map is None or self.start_x is None:
            if self.start_x is None:
                self.get_logger().warning("⏳ [PLANNER] Meta recibida, pero aún no hay datos de /odom.")
            return

        goal_x = msg.pose.position.x
        goal_y = msg.pose.position.y

        start_g = self.world_to_grid(self.start_x, self.start_y)
        goal_g = self.world_to_grid(goal_x, goal_y)

        self.get_logger().info(f"🔍 [PLANNER] Procesando meta A*...")
        path_grid = self.a_star(start_g, goal_g)

        if path_grid:
            self.publish_path(path_grid, msg.header)
            self.get_logger().info(f"✅ [PLANNER] Ruta publicada ({len(path_grid)} nodos).")
        else:
            self.get_logger().error("❌ [PLANNER] A* falló por completo.")

    def a_star(self, start, goal):
        neighbors = [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
        def heuristic(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

        if not (0 <= goal[0] < self.map_info.width and 0 <= goal[1] < self.map_info.height): 
            return []
            
        if self.inflated_map[goal[1], goal[0]] > 50:
            self.get_logger().warning("🚫 [PLANNER] Meta en PARED INFLADA. Buscando celda libre cercana...")
            goal = self.find_nearest_free_cell(goal)
            if goal is None:
                return []
                
        if self.inflated_map[start[1], start[0]] > 50:
            self.get_logger().warning("⚠️ [PLANNER] Robot dentro de PARED INFLADA. Buscando salida...")
            start = self.find_nearest_free_cell(start)
            if start is None:
                return []

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        
        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.reverse()
                return path

            for dx, dy in neighbors:
                neighbor = (current[0] + dx, current[1] + dy)
                if 0 <= neighbor[0] < self.map_info.width and 0 <= neighbor[1] < self.map_info.height:
                    if self.inflated_map[neighbor[1], neighbor[0]] > 50:
                        continue
                    
                    move_cost = math.hypot(dx, dy)
                    tentative_g = g_score[current] + move_cost
                    
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + heuristic(neighbor, goal)
                        heapq.heappush(open_set, (f_score, neighbor))
        return [] 

    def publish_path(self, path_grid, header):
        path_msg = Path()
        path_msg.header = header
        path_msg.header.frame_id = "map"

        for gx, gy in path_grid:
            pose = PoseStamped()
            pose.header = path_msg.header
            wx, wy = self.grid_to_world(gx, gy)
            pose.pose.position.x = wx
            pose.pose.position.y = wy
            pose.pose.orientation.w = 1.0 
            path_msg.poses.append(pose)

        self.path_pub.publish(path_msg)

def main():
    rclpy.init()
    node = GlobalPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Traductor de coordenadas
        Node(
            package='maze_nav',
            executable='tf_to_pose',
            name='tf_to_pose',
            output='screen'
        ),
        
        # 2. Planificador Global A*
        Node(
            package='maze_nav',
            executable='global_planner',
            name='global_planner',
            output='screen'
        ),
        
        # 3. Seguidor de Ruta (Lyapunov)
        Node(
            package='maze_nav',
            executable='wall_follower',
            name='wall_follower',
            output='screen'
        ),
        
        # 4. El Puente Multihilo
        Node(
            package='maze_nav',
            executable='explore_bridge',
            name='explore_bridge',
            output='screen'
        ),
        
        # 5. El nodo de Exploración (Explore Lite)
        Node(
            package='explore_lite',
            executable='explore',
            name='explore_node',
            output='screen',
            parameters=[{'visualize': True}]
        )
    ])

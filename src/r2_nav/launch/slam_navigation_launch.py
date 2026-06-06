import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Get the launch directories
    r2_nav_dir = get_package_share_directory('r2_nav')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # Create the launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time')
    params_file = LaunchConfiguration('params_file')
    default_bt_xml_filename = LaunchConfiguration('default_bt_xml_filename')
    autostart = LaunchConfiguration('autostart')

    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true')

    declare_params_file_cmd = DeclareLaunchArgument(
        'params_file',
        default_value='/root/smart_warehouse_robot/src/r2_nav/config/nav2_params.yaml',
        description='Full path to the ROS2 parameters file to use for all launched nodes')

    declare_bt_xml_cmd = DeclareLaunchArgument(
        'default_bt_xml_filename',
        default_value='/root/smart_warehouse_robot/src/r2_nav/behavior_trees/minimal_bt.xml',
        description='Full path to the behavior tree xml file to use')

    declare_autostart_cmd = DeclareLaunchArgument(
        'autostart', default_value='true',
        description='Automatically startup the nav2 stack')

    # 1. Start SLAM Toolbox in Localization Mode
    # It will use the configuration defined in the compiled slam_toolbox config directory
    slam_toolbox_localization_node = Node(
        parameters=[
            os.path.join(get_package_share_directory('slam_toolbox'), 'config', 'mapper_params_localization.yaml')
        ],
        package='slam_toolbox',
        executable='localization_slam_toolbox_node',
        name='slam_toolbox',
        output='screen'
    )

    # 2. Start Nav2 Navigation (planner, controller, recoveries, bt_navigator, waypoint_follower)
    # Note: map_server and amcl are not launched here because SLAM Toolbox handles localization and map serving
    navigation_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time,
                          'autostart': autostart,
                          'params_file': params_file,
                          'default_bt_xml_filename': default_bt_xml_filename,
                          'use_lifecycle_mgr': 'false',
                          'map_subscribe_transient_local': 'true'}.items()
    )

    # 3. Lifecycle Manager to transition the navigation nodes to active state
    # Excludes map_server and amcl as they are replaced by slam_toolbox
    lifecycle_manager_navigation_node = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time},
                    {'autostart': autostart},
                    {'node_names': ['controller_server',
                                    'planner_server',
                                    'recoveries_server',
                                    'bt_navigator',
                                    'waypoint_follower']}]
    )

    # Create the launch description and populate
    ld = LaunchDescription()

    # Declare the launch options
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_params_file_cmd)
    ld.add_action(declare_autostart_cmd)
    ld.add_action(declare_bt_xml_cmd)

    # Add the nodes and launch commands
    ld.add_action(slam_toolbox_localization_node)
    ld.add_action(navigation_cmd)
    ld.add_action(lifecycle_manager_navigation_node)

    return ld

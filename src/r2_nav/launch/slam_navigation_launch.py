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
    # Pointing directly to the absolute path of the configuration file in the original workspace source tree
    slam_toolbox_localization_node = Node(
        parameters=[
            '/root/smart_warehouse_robot/src/slam_toolbox/config/mapper_params_localization.yaml'
        ],
        package='slam_toolbox',
        executable='localization_slam_toolbox_node',
        name='slam_toolbox',
        output='screen'
    )

    # 2. Start Nav2 Navigation (planner, controller, recoveries, bt_navigator, waypoint_follower)
    # Note: navigation_launch.py already starts its own lifecycle manager for these 5 nodes,
    # so we do not launch a separate lifecycle manager here to avoid conflicts.
    navigation_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')),
        launch_arguments={'use_sim_time': use_sim_time,
                          'autostart': autostart,
                          'params_file': params_file,
                          'default_bt_xml_filename': default_bt_xml_filename,
                          'map_subscribe_transient_local': 'true'}.items()
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

    return ld

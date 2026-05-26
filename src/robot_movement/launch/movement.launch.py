from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_movement',
            executable='servo_node',
            name='servo_node',
            output='screen',
        ),
        Node(
            package='robot_movement',
            executable='esc_node',
            name='esc_node',
            output='screen',
        )
    ])
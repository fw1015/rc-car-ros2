from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_brain',
            executable='robot_brain_node',
            name='brain_node',
            output='screen',
        ),
    ])
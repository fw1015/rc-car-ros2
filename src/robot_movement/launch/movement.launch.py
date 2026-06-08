from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='robot_movement',
            executable='i2c_manager',
            name='i2c_manager',
            output='screen',
        )
    ])
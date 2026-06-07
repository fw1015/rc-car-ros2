from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # 1. Web Server Node
        Node(
            package='web_interface',
            executable='web_server_node',
            name='web_server_node',
            output='screen',
            parameters=[],
        ),
        
        # 2. Brain Node (Obstacle Avoidance)
        Node(
            package='robot_brain',
            executable='robot_brain_node',
            name='robot_brain_node',
            output='screen',
        ),

        # 3. i2c Manager Node (Sensor Data Handling)
        Node(
            package='robot_movement',
            executable='i2c_manager',
            name='i2c_manager',
            output='screen',
        ),

        # 4. Tof Sensor Node (Throttle)
        Node(
            package='robot_sensors',
            executable='tof_sensor_node',
            name='tof_sensor_node',
            output='screen',
        ),

        # 5. Ultrasonic Sensor Node (Throttle)
        Node(
            package='robot_sensors',
            executable='ultrasound_sensor_node',
            name='ultrasound_sensor_node',
            output='screen',
        ),

        # 6. Camera Node (Video Streaming)
        Node(
            package='camera_ros',
            executable='camera_node',
            name='camera_node',
            output='screen',
            parameters=[
                {'camera_name': 'pi_cam'},
                {'width': 854},
                {'height': 480},
                {'frame_rate': 15},
                {'use_compressed': True},
                {'camera': '/base/axi/pcie@120000/rp1/i2c@80000/imx708@1a'},   # Force camera
            ],
            arguments=['--ros-args', '--log-level', 'info']
        ),

        # 7. Web Sever
        Node(
            package='web_video_server',
            executable='web_video_server',
            name='web_video_server',
            output='screen',
            parameters=[{'port': 8080}]
        ),
    ])
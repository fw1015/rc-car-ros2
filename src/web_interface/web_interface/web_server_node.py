import os
import threading
import rclpy
from rclpy.node import Node
from flask import Flask, render_template, jsonify, request, Response
from std_msgs.msg import Float64
from sensor_msgs.msg import Range
from geometry_msgs.msg import Twist, Vector3
import requests
import subprocess
import csv
import time
import datetime

class WebServerNode(Node):
    """
    Teleoperation Web Server Node

    Responsibilities:
    - Hosts the Flask web dashboard serving the HTML/JS/CSS frontend
    - Subscribes to hardware sensor topics and serves telemetry via JSON endpoints
    - Proxies the MJPEG camera stream from web_video_server
    - Receives HTTP POST commands from the web UI and publishes them as ROS 2 Twist messages
    """

    def __init__(self):
        super().__init__('web_server_node')
        
        # Publisher for raw commands coming from the web interface
        self.publisher = self.create_publisher(Twist, '/cmd_vel_raw', 10)
        self.pid_publisher = self.create_publisher(Vector3, '/pid_tuning', 10)
        
        # Subscriptions for adjusted commands after processing in the Robot Brain
        self.create_subscription(Twist, '/cmd_vel_adjusted', self.adjusted_callback, 10)

        # Subscriptions to sensor topics
        self.create_subscription(Float64, '/tof/distance', self.front_callback, 10)
        self.create_subscription(Range, '/left_distance', self.left_callback, 10)
        self.create_subscription(Range, '/right_distance', self.right_callback, 10)
        
        # Telemetry State Memory
        self.latest_front_distance = None
        self.latest_left_distance = None
        self.latest_right_distance = None

        # Command State
        self.steering = 0.0
        self.steering_step = 0.15
        self.thrust = 0.0
        self.thrust_step = 0.25
        self.thrust_max = 0.9
        self.adj_thrust = 0.0
        self.adj_steering = 0.0

        # PID State
        self.kp = 1.0
        self.ki = 0.0
        self.kd = 0.5

        # Flask App Initialization
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, 'templates')
        self.app = Flask(__name__, template_folder=template_dir)

        self._setup_flask_routes()

        # Telemetry State Variables
        self.is_logging = False
        self.csv_file = None
        self.csv_writer = None
        
        self.create_timer(0.1, self.log_telemetry)
    
    def _setup_flask_routes(self):
        """Configures all HTTP endpoints for the Flask application"""

        @self.app.route('/')
        def index():
            """Serves the main teleoperation dashboard"""
            return render_template('index.html')

        @self.app.route('/sensor_data')
        def sensor_data():
            """Provides real-time telemetry data to the frontend UI"""
            return jsonify({
                'front': self.latest_front_distance,
                'left': self.latest_left_distance,
                'right': self.latest_right_distance,
                'throttle_raw': self.thrust,
                'throttle_adjusted': self.adj_thrust,
                'steering_raw': self.steering,
                'steering_adjusted': self.adj_steering
            })

        @self.app.route('/camera_stream')
        def camera_stream():
            """Proxies the MJPEG stream from the local web_video_server to avoid CORS issues"""
            def generate():
                try:
                    r = requests.get(
                        "http://127.0.0.1:8080/stream?topic=/camera_node/image_raw&type=ros_compressed&quality=35",
                        stream=True,
                        timeout=10
                    )
                    r.raise_for_status()
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                except Exception as e:
                    self.get_logger().error(f"Camera proxy error: {e}")
                    yield b''  # Return empty to avoid crash
            return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

        @self.app.route('/command', methods=['POST'])
        def command():
            """Receives touch-screen commands, accumulates and publishes Twist"""
            data = request.get_json()
            cmd_type = data.get('type')
            value = data.get('value')

            # Handle Configuration Settings (Max Speed Limiter)
            if cmd_type == 'setting':
                if data.get('target') == 'max_speed':
                    self.thrust_max = float(value)
                    # Clamp current thrust down immediately if we lower the speed limit while driving
                    if abs(self.thrust) > self.thrust_max:
                        self.thrust = self.thrust_max if self.thrust > 0 else -self.thrust_max
                    
                    self.get_logger().info(f'Speed Governor updated to: {self.thrust_max:.2f}')
                    return jsonify({'status': 'ok'})

            # Handle PID
            elif cmd_type == 'pid_tune':
                self.kp = float(data.get('kp', 1.0))
                self.ki = float(data.get('ki', 0.0))
                self.kd = float(data.get('kd', 0.5))

                pid_msg = Vector3()
                pid_msg.x = self.kp
                pid_msg.y = self.ki
                pid_msg.z = self.kd
                
                self.pid_publisher.publish(pid_msg)
                self.get_logger().info(f"Live Tune Relayed -> Kp: {pid_msg.x} | Ki: {pid_msg.y} | Kd: {pid_msg.z}")
                return jsonify({'status': 'ok'})

            # Update Steering State
            elif cmd_type == 'direction':
                if value == 'left':
                    steering_count = self.steering + self.steering_step
                    self.steering = min(1.0, steering_count)
                elif value == 'right':
                    steering_count = self.steering - self.steering_step
                    self.steering = max(-1.0, steering_count)
                elif value == 'stop':
                    # Snaps the steering back to a 1500us neutral pulse
                    self.steering = 0.0
                
            # Update Throttle State
            elif cmd_type == 'throttle':
                if value == 'forward':
                    thrust_count = self.thrust + self.thrust_step
                    self.thrust = min(self.thrust_max, thrust_count)
                elif value == 'reverse':
                    thrust_count = self.thrust - self.thrust_step
                    self.thrust = max(-self.thrust_max, thrust_count)
                elif value == 'brake' or value == 'stop':
                    # Snaps the ESC back to a 1500us neutral pulse
                    self.thrust = 0.0
            
            # Construct and Publish ROS 2 Twist Message
            twist = Twist()
            twist.angular.z = self.steering
            twist.linear.x = self.thrust

            self.publisher.publish(twist)
            return jsonify({'status': 'ok'})
        
        @self.app.route('/toggle_logging', methods=['POST'])
        def toggle_logging():
            """Starts or stops the CSV telemetry logging dynamically"""
            data = request.get_json()
            enable = data.get('enable')

            if enable and not self.is_logging:
                # START LOGGING: Generate the timestamped file NOW
                log_dir = '/home/fwann/Documents/Project/ros2_robot_ws/telemetry'
                os.makedirs(log_dir, exist_ok=True) 
                
                current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                file_path = os.path.join(log_dir, f'telemetry_log_{current_time}.csv')
                
                self.csv_file = open(file_path, mode='w', newline='')
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow([
                    'Timestamp', 
                    'Front_cm', 'Left_cm', 'Right_cm', 
                    'Thrust_Raw', 'Thrust_Adjusted', 'Steering_Raw', 'Steering_Adjusted', 
                    'Kp', 'Ki', 'Kd'
                ])
                
                self.is_logging = True
                self.get_logger().info(f"Started logging to {file_path}")
                return jsonify({'status': 'ok'})

            elif not enable and self.is_logging:
                # STOP LOGGING: Safely close the file to save the data
                self.is_logging = False
                if self.csv_file:
                    self.csv_file.close()
                self.get_logger().info("Telemetry logging stopped and saved.")
                return jsonify({'status': 'ok'})

            return jsonify({'status': 'ignored'})

        @self.app.route('/shutdown', methods=['POST'])
        def shutdown_system():
            """Triggers complete hardware shutdown of the Raspberry Pi"""
            try:
                self.get_logger().warn("HARDWARE SHUTDOWN command received from web interface!")

                subprocess.Popen('sleep 2 && sudo /sbin/poweroff', shell=True)

                self.get_logger().info("Poweroff sequence initiated. System will halt in 2 seconds.")
                return jsonify({'status': 'ok'})

            except Exception as e:
                self.get_logger().error(f"Exception during shutdown: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

    def adjusted_callback(self, msg):
        """Update adjusted command values"""
        self.adj_thrust = msg.linear.x
        self.adj_steering = msg.angular.z

    def front_callback(self, msg):
        """Update latest front distance from ToF sensor (Convert to cm for UI)"""
        distance_cm = msg.data * 100
        self.latest_front_distance = distance_cm
        self.get_logger().info(f'Front Distance: {distance_cm:.1f} cm')

    def left_callback(self, msg):
        """Update latest left distance from ultrasonic sensor (Convert to cm for UI)"""
        distance_cm = max(0.0, msg.range * 100 - 7)
        self.latest_left_distance = distance_cm
        self.get_logger().info(f'Left Distance: {distance_cm:.1f} cm')

    def right_callback(self, msg):
        """Update latest right distance from ultrasonic sensor (Convert to cm for UI)"""
        distance_cm = max(0.0, msg.range * 100 - 7)
        self.latest_right_distance = distance_cm
        self.get_logger().info(f'Right Distance: {distance_cm:.1f} cm')

    def run_flask(self):
        """Blocking call to start the Flask server. Must be run in a separate thread"""
        self.get_logger().info('Web server started → http://192.168.0.30:5000')
        self.app.run(host='0.0.0.0', port=5000, debug=False)

    def start(self):
        """Spawns the Flask web server in a background daemon thread"""
        self.server_thread = threading.Thread(target=self.run_flask, daemon=True)
        self.server_thread.start()

    def log_telemetry(self):
        """Logs telemetry data to CSV for offline analysis"""
        if not self.is_logging or self.csv_writer is None:
            return
        
        timestamp = time.time()
        self.csv_writer.writerow([
            timestamp,
            self.latest_front_distance,
            self.latest_left_distance,
            self.latest_right_distance,
            self.thrust,
            self.adj_thrust,
            self.steering,
            self.adj_steering,
            self.kp,
            self.ki,
            self.kd
        ])
        self.csv_file.flush()


def main(args=None):
    rclpy.init(args=args)
    node = WebServerNode()
    node.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down WebServerNode...')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
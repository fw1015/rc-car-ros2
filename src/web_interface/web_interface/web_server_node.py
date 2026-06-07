import os
import threading
import rclpy
from rclpy.node import Node
from flask import Flask, render_template, jsonify, request, Response
from std_msgs.msg import Float64
from sensor_msgs.msg import Range
from geometry_msgs.msg import Twist
import requests


class WebServerNode(Node):
    """
    Teleoperation Web Server Node.

    Responsibilities:
    - Hosts the Flask web dashboard serving the HTML/JS/CSS frontend.
    - Subscribes to hardware sensor topics and serves telemetry via JSON endpoints.
    - Proxies the MJPEG camera stream from web_video_server.
    - Receives HTTP POST commands from the web UI and publishes them as ROS 2 Twist messages.
    """

    def __init__(self):
        super().__init__('web_server_node')
        
        # Publisher for raw commands coming from the web interface
        self.publisher = self.create_publisher(Twist, '/cmd_vel_raw', 10)

        # Subscriptions to sensor topics
        self.create_subscription(Float64, '/tof/distance', self.front_callback, 10)
        self.create_subscription(Range, '/left_distance', self.left_callback, 10)
        self.create_subscription(Range, '/right_distance', self.right_callback, 10)
        
        # Telemetry State Memory
        self.latest_front_distance = None
        self.latest_left_distance = None
        self.latest_right_distance = None

        # Command state
        self.steering = 0.0
        self.steering_step = 0.15
        self.thrust = 0.0
        self.thrust_step = 0.25
        self.thrust_max = 0.9

        # Flask App Initialization
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, 'templates')
        self.app = Flask(__name__, template_folder=template_dir)

        self._setup_flask_routes()

    
    def _setup_flask_routes(self):
        """Configures all HTTP endpoints for the Flask application."""

        @self.app.route('/')
        def index():
            """Serves the main teleoperation dashboard."""
            return render_template('index.html')

        @self.app.route('/sensor_data')
        def sensor_data():
            """Provides real-time telemetry data to the frontend UI."""
            return jsonify({
                'front': self.latest_front_distance,
                'left': self.latest_left_distance,
                'right': self.latest_right_distance,
                'throttle': self.thrust,
                'steering': self.steering
            })

        @self.app.route('/camera_stream')
        def camera_stream():
            """Proxies the MJPEG stream from the local web_video_server to avoid CORS issues."""
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
            """Receives touch-screen joystick commands, accumulates them, and publishes Twist."""
            data = request.get_json()
            cmd_type = data.get('type')
            value = data.get('value')

            # Update Steering State
            if cmd_type == 'direction':
                if value == 'left':
                    self.steering = min(1.0, self.steering + self.steering_step)
                elif value == 'right':
                    self.steering = max(-1.0, self.steering - self.steering_step)
                elif value == 'stop':
                    self.steering = 0.0
                
            # Update Throttle State
            elif cmd_type == 'throttle':
                if value == 'forward':
                    self.thrust = min(self.thrust_max, self.thrust + self.thrust_step)
                elif value == 'reverse':
                    self.thrust = max(-self.thrust_max, self.thrust - self.thrust_step)
                elif value == 'brake' or value == 'stop':
                    # Snaps the ESC back to a 1500us neutral pulse
                    self.thrust = 0.0
            
            # Construct and Publish ROS 2 Twist Message
            twist = Twist()
            twist.angular.z = self.steering
            twist.linear.x = self.thrust

            self.publisher.publish(twist)
            return jsonify({'status': 'ok'})

    def front_callback(self, msg):
        """Update latest front distance from ToF sensor (Convert to cm for UI)."""
        distance_cm = msg.data * 100
        self.latest_front_distance = distance_cm
        self.get_logger().info(f'Front Distance: {distance_cm:.1f} cm')

    def left_callback(self, msg):
        """Update latest left distance from ultrasonic sensor (Convert to cm for UI)."""
        distance_cm = msg.range * 100
        self.latest_left_distance = distance_cm
        self.get_logger().info(f'Left Distance: {distance_cm:.1f} cm')

    def right_callback(self, msg):
        """Update latest right distance from ultrasonic sensor (Convert to cm for UI)."""
        distance_cm = msg.range * 100
        self.latest_right_distance = distance_cm
        self.get_logger().info(f'Right Distance: {distance_cm:.1f} cm')

    def run_flask(self):
        """Blocking call to start the Flask server. Must be run in a separate thread."""
        self.get_logger().info('Web server started → http://192.168.0.30:5000')
        self.app.run(host='0.0.0.0', port=5000, debug=False)

    def start(self):
        """Spawns the Flask web server in a background daemon thread."""
        self.server_thread = threading.Thread(target=self.run_flask, daemon=True)
        self.server_thread.start()


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
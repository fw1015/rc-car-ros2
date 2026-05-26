import os
import threading
import rclpy
from rclpy.node import Node
from flask import Flask, render_template, jsonify, request
from std_msgs.msg import Float64
from sensor_msgs.msg import Range
from geometry_msgs.msg import Twist
import requests


class WebServerNode(Node):
    def __init__(self):
        super().__init__('web_server_node')
        
        self.publisher = self.create_publisher(Twist, '/cmd_vel_raw', 10)
        
        self.latest_front_distance = None
        self.latest_left_distance = None
        self.latest_right_distance = None

        self.create_subscription(Float64, '/tof/distance', self.front_callback, 10)
        self.create_subscription(Range, '/left_distance', self.left_callback, 10)
        self.create_subscription(Range, '/right_distance', self.right_callback, 10)

        self.steering = 0.0
        self.steering_step = 0.15
        self.thrust = 0.0
        self.thrust_step = 0.25
        self.thrust_max = 0.9

        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, 'templates')
        self.app = Flask(__name__, template_folder=template_dir)

        @self.app.route('/')
        def index():
            return render_template('index.html')

        # === Sensor Data ===
        @self.app.route('/sensor_data')
        def sensor_data():
            return jsonify({
                'front': self.latest_front_distance,
                'left': self.latest_left_distance,
                'right': self.latest_right_distance
            })

        # === Camera Stream ===
        @self.app.route('/camera_stream')
        def camera_stream():
            def generate():
                try:
                    r = requests.get(
                        "http://127.0.0.1:8080/stream?topic=/camera_node/image_raw&type=ros_compressed",
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

        # === Command Handler (AJAX) ===
        @self.app.route('/command', methods=['POST'])
        def command():
            data = request.get_json()
            cmd_type = data.get('type')
            value = data.get('value')

            if cmd_type == 'direction':
                if value == 'left':
                    self.steering = min(1.0, self.steering + self.steering_step)
                elif value == 'right':
                    self.steering = max(-1.0, self.steering - self.steering_step)
                elif value == 'stop':
                    self.steering = 0.0
                

            elif cmd_type == 'throttle':
                if value == 'forward':
                    self.thrust = min(self.thrust_max, self.thrust + self.thrust_step)
                else:
                    self.thrust = 0.0
                
            twist = Twist()
            twist.angular.z = self.steering
            twist.linear.x = self.thrust

            self.publisher.publish(twist)
            self.get_logger().info(f'Command → Thrust:{self.thrust:.2f} Steering:{self.steering:+.2f}')

            return jsonify({'status': 'ok'})

        self.get_logger().info('Web server started → http://192.168.0.30:5000')

    def front_callback(self, msg):
        distance_cm = msg.data * 100
        self.latest_front_distance = distance_cm
        self.get_logger().info(f'Front Distance: {distance_cm:.1f} cm')

    def left_callback(self, msg):
        distance_cm = msg.range * 100
        self.latest_left_distance = distance_cm
        self.get_logger().info(f'Left Distance: {distance_cm:.1f} cm')

    def right_callback(self, msg):
        distance_cm = msg.range * 100
        self.latest_right_distance = distance_cm
        self.get_logger().info(f'Right Distance: {distance_cm:.1f} cm')

    def run_flask(self):
        self.app.run(host='0.0.0.0', port=5000, debug=False)

    def start(self):
        self.server_thread = threading.Thread(target=self.run_flask, daemon=True)
        self.server_thread.start()


def main(args=None):
    rclpy.init(args=args)
    node = WebServerNode()
    node.start()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
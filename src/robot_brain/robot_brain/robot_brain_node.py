import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
from robot_movement.srv import SetESCServo
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class RobotBrainNode(Node):
    """
    Central decision-making node for the autonomous RC vehicle.
    
    Responsibilities:
    - Receives raw movement commands from the web interface.
    - Applies sensor-fusion logic (obstacle avoidance) to calculate safe velocities.
    - Forwards validated commands to the I2C Manager via service calls.
    - Enforces a dead-man's switch safety timeout to halt the vehicle on connection loss.
    """

    def __init__(self):
        super().__init__('robot_brain_node')

        # QoS Profile: Optimized for low-latency, real-time phone control over WiFi
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Subscriptions
        self.create_subscription(Float64, '/tof/distance', self.front_dist_callback, 10)
        self.create_subscription(Twist, '/cmd_vel_raw', self.move_cmd_callback, qos_profile)

        # Service Clients
        self.esc_servo_client = self.create_client(SetESCServo, 'set_esc_servo')

        # State memory
        self.front_distance = None
        self.last_raw_throttle = None
        self.last_raw_steering = None

        # Safety Timer
        self.last_cmd_time = self.get_clock().now()
        self.safety_active = False
        self.create_timer(0.2, self.safety_check)

        self.get_logger().info('✅ Robot Brain Node started: Teleoperation & Safety active.')

    def front_dist_callback(self, msg: Float64):
        """Updates the internal state with the latest valid ToF distance in meters."""
        self.front_distance = msg.data

    def move_cmd_callback(self, msg: Twist):
        """
        Processes incoming joystick commands, applies safety adjustments, 
        and dispatches them to the motor controller.
        """
        self.last_cmd_time = self.get_clock().now()
        self.safety_active = False

        # Throttle processing (Includes obstacle avoidance logic)
        if msg.linear.x != self.last_raw_throttle:
            self.sensor_control_adjust(msg)

        # Steering processing (Direct passthrough)
        if msg.angular.z != self.last_raw_steering:
            self.send_command(channel=2, value=msg.angular.z)
            self.last_raw_steering = msg.angular.z

    def sensor_control_adjust(self, msg: Twist):
        """
        Dynamic Obstacle Avoidance: Adjusts forward throttle based on proximity.
        """
        adjusted_throttle = msg.linear.x
        
        # Only apply safety brakes if the user is trying to drive FORWARD
        if adjusted_throttle > 0.0 and self.front_distance is not None:

            if self.front_distance < 0.15:  
                # CRITICAL STOP: Less than 15cm. Override user completely.
                adjusted_throttle = min(0.0, adjusted_throttle)
                self.get_logger().warn(f"🚧 Wall at {self.front_distance:.2f}m! Forward motion disabled.")
                
            elif self.front_distance < 1.0: 
                # PROXIMITY CRAWL: Between 15cm and 1 meter. 
                # Throttle is linearly clamped by distance (e.g., 0.6m away = 60% max throttle)
                max_allowed_throttle = self.front_distance
                
                if adjusted_throttle > max_allowed_throttle:
                    adjusted_throttle = max_allowed_throttle
                    
        # Dispatch the adjusted command
        self.send_command(channel=0, value=adjusted_throttle)
        
        # Save state to prevent spamming the I2C bus with duplicate values
        self.last_raw_throttle = adjusted_throttle

    def send_command(self, channel: int, value: float):
        """Asynchronously dispatches hardware commands via the SetESCServo service."""
        if not self.esc_servo_client.service_is_ready():
            self.get_logger().warn('I2CManager service not ready yet')
            return

        request = SetESCServo.Request()
        request.channel = channel
        request.value = value

        future = self.esc_servo_client.call_async(request)
        future.add_done_callback(self.service_response_callback)

    def service_response_callback(self, future):
        """Handles the response from the I2C Manager (Logs failures only)."""
        try:
            response = future.result()
            if not response.success:
                self.get_logger().error(f'I2CManager failed: {response.message}')
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')

    def safety_check(self):
        """
        Watchdog Timer: Halts the vehicle if the web interface disconnects 
        or stops sending commands for more than 0.5 seconds.
        """
        time_since_last = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9

        if time_since_last > 0.5:
            if not self.safety_active:
                self.get_logger().warn('No command received for 0.5s → Sending neutral (safety mode)')
                self.safety_active = True

            # Force neutral state for both ESC and Servo
            self.send_command(channel=0, value=0.0)
            self.send_command(channel=2, value=0.0)

            # Reset local state to ensure next command passes the spam filter
            self.last_raw_throttle = 0.0
            self.last_raw_steering = 0.0
    
    


def main(args=None):
    rclpy.init(args=args)
    node = RobotBrainNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Robot Brain Node...')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
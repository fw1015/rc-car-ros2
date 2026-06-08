import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
from robot_movement.srv import SetESCServo
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy

class RobotBrainNode(Node):
    """
    Central decision-making node for the RC Car
    
    Responsibilities:
    - Receives raw movement commands from the web interface (from user)
    - Applies sensor-fusion logic (obstacle avoidance) to calculate safe velocities and braking logics
    - Forwards validated commands to the I2C Manager via service calls
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

        # Publisher for adjusted commands after processing in the Robot Brain
        self.adjusted_publisher = self.create_publisher(Twist, '/cmd_vel_adjusted', 10)

        # Subscriptions to sensor data and raw commands
        self.create_subscription(Float64, '/tof/distance', self.front_dist_callback, 10)
        self.create_subscription(Twist, '/cmd_vel_raw', self.move_cmd_callback, qos_profile)

        # Service Clients to send commands to the I2C Manager
        self.esc_servo_client = self.create_client(SetESCServo, 'set_esc_servo')

        # State memory for sensor readings and last commands (used for safety checks and active braking)
        self.front_distance = None
        self.last_raw_throttle = 0.0
        self.last_adjusted_throttle = 0.0
        self.last_steering = 0.0

        # Asynchronous timer for Active Braking (used to release brakes after a timed duration)
        self.brake_timer = None

        # Safety Timer to detect loss of command input (e.g., web interface disconnect)
        self.last_cmd_time = self.get_clock().now()
        self.safety_active = False
        self.create_timer(0.2, self.safety_check)

        self.get_logger().info('✅ Robot Brain Node started: Teleoperation & Safety active.')

    def front_dist_callback(self, msg: Float64):
        """Updates the internal state with the true bumper-to-obstacle distance."""
        # Hardware Offset: Sensor is 22mm (0.022m) behind the physical front bumper
        # Subtract 0.022m, clamping at 0.0 to prevent negative distances
        self.front_distance = max(0.0, msg.data - 0.022)

        if self.last_raw_throttle > 0.0:
            temp_msg = Twist()
            temp_msg.linear.x = self.last_raw_throttle
            self.sensor_control_adjust(temp_msg)

    def move_cmd_callback(self, msg: Twist):
        """Processes incoming joystick commands, 
        applies safety adjustments, and dispatches them to the motor controller"""
        self.last_cmd_time = self.get_clock().now()
        self.safety_active = False

        self.last_raw_throttle = msg.linear.x
        self.sensor_control_adjust(msg)

        # Steering processing (Direct passthrough)
        if msg.angular.z != self.last_steering:
            self.send_command(channel=2, value=msg.angular.z)
            self.last_steering = msg.angular.z

    def sensor_control_adjust(self, msg: Twist):
        """Dynamic Obstacle Avoidance: Enforces a 1.5-meter Deceleration Zone 
        where forward throttle is linearly clamped based on true bumper distance"""
        adjusted_throttle = msg.linear.x
        
        # Only apply safety brakes if the user is trying to drive FORWARD
        if adjusted_throttle > 0.0 and self.front_distance is not None:

            # 1. HARD STOP
            if self.front_distance < 0.08:
                adjusted_throttle = min(0.0, adjusted_throttle)
                self.get_logger().warn(f"🚧 Wall at {self.front_distance:.2f}m! Emergency Stop.")
                
            # 2. DECELERATION ZONE (<= 1.50 meter)
            # Adjusted Throttle = Distance / 3.0 (e.g., 1.5m = 0.50, 0.3m = 0.10)
            elif self.front_distance <= 1.50: 
                max_allowed_throttle = self.front_distance / 3.5
                if adjusted_throttle > max_allowed_throttle:
                    adjusted_throttle = max_allowed_throttle
                    
        # 3. SPAM FILTER & BRAKE LOGIC
        if adjusted_throttle != self.last_adjusted_throttle:
            
            # ACTIVE BRAKING
            if adjusted_throttle == 0.0 and self.last_adjusted_throttle > 0.0:
                self.engage_active_brake(self.last_adjusted_throttle)
            else:
                if self.brake_timer is not None:
                    self.brake_timer.cancel()
                    self.brake_timer = None
                
                # DEADBAND BOOST - minimum crawl speed as 0.15 to prevent stalling in tight maneuvers
                if 0.0 < adjusted_throttle < 0.15:
                    adjusted_throttle = 0.15

                self.send_command(channel=0, value=adjusted_throttle)

            # Publish the state to the UI
            pub_msg = Twist()
            pub_msg.linear.x = float(adjusted_throttle)
            pub_msg.angular.z = float(self.last_steering)
            self.adjusted_publisher.publish(pub_msg)
            
            self.last_adjusted_throttle = adjusted_throttle

    def engage_active_brake(self, previous_velocity: float) -> None:
        """Active Braking: Applies 1.5x negative brake force with a stepped duration based on velocity"""
        if self.brake_timer is not None:
            self.brake_timer.cancel()
            self.brake_timer = None
        
        # 1. FORCE CALCULATION
        brake_force = -previous_velocity * 1.5
        
        # 2. STEPPED DURATION
        # Categorized timers based on how fast the car was going
        abs_vel = abs(previous_velocity)
        if abs_vel <= 0.25:
            brake_duration = 0.20
        elif abs_vel <= 0.50:
            brake_duration = 0.25
        elif abs_vel <= 0.75:
            brake_duration = 0.30
        else:
            brake_duration = 0.50
        
        # Dispatch the brake command
        self.send_command(channel=0, value=brake_force)
        self.get_logger().info(f"🛑 Active Braking: Pulsing {brake_force:.2f} thrust for {brake_duration}s")
        
        # Start a single-shot timer to release the brakes automatically
        self.brake_timer = self.create_timer(brake_duration, self.release_brake)

    def release_brake(self) -> None:
        """Returns the ESC to absolute neutral"""
        self.send_command(channel=0, value=0.0)
        self.get_logger().info("⚪ Brakes Released -> Neutral Coast")
        
        if self.brake_timer is not None:
            self.brake_timer.cancel()
            self.brake_timer = None

    def send_command(self, channel: int, value: float):
        """Asynchronously dispatches hardware commands via the SetESCServo service"""
        if not self.esc_servo_client.service_is_ready():
            self.get_logger().warn('I2CManager service not ready yet')
            return

        request = SetESCServo.Request()
        request.channel = channel
        request.value = value

        future = self.esc_servo_client.call_async(request)
        future.add_done_callback(self.service_response_callback)

    def service_response_callback(self, future):
        """Handles the response from the I2C Manager (Logs failures only)"""
        try:
            response = future.result()
            if not response.success:
                self.get_logger().error(f'I2CManager failed: {response.message}')
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')

    def safety_check(self):
        """Watchdog Timer - Halts the vehicle if the web interface disconnects 
        or stops sending commands for more than 0.5 seconds"""
        time_since_last = (self.get_clock().now() - self.last_cmd_time).nanoseconds / 1e9

        if time_since_last > 0.5:
            if not self.safety_active:
                self.get_logger().warn('No command received for 0.5s → Sending neutral (safety mode)')
                self.safety_active = True

            # Force neutral state for both ESC and Servo
            self.send_command(channel=0, value=0.0)
            self.send_command(channel=2, value=0.0)

            # Reset local state 
            self.last_raw_throttle = 0.0
            self.last_adjusted_throttle = 0.0
            self.last_steering = 0.0

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
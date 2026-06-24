import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist, Vector3
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
        self.create_subscription(Vector3, '/pid_tuning', self.pid_tune_callback, 10)

        # Service Clients to send commands to the I2C Manager
        self.esc_servo_client = self.create_client(SetESCServo, 'set_esc_servo')

        # State memory for sensor readings and last commands (used for safety checks and active braking)
        self.front_distance = None
        self.last_raw_throttle = 0.0
        self.last_adjusted_throttle = 0.0
        self.last_steering = 0.0

        # PID Controller Settings
        self.target_distance = 0.10     # Stop exactly 10cm from the wall
        self.kp = 1.0                   # Proportional gain
        self.ki = 0.0                   # Integral gain
        self.kd = 0.5                   # Derivative gain (The shock absorber)
        self.last_error = 0.0
        self.integral_error = 0.0
        self.last_pid_time = self.get_clock().now()

        # Safety Timer to detect loss of command input (e.g., web interface disconnect)
        self.last_cmd_time = self.get_clock().now()
        self.safety_active = False
        self.create_timer(0.2, self.safety_check)

        self.get_logger().info('✅ Robot Brain Node started: Teleoperation & Safety active.')

    def front_dist_callback(self, msg: Float64):
        """Updates the internal state and runs the PID loop at the sensor's native rate"""
        # Hardware Offset: Sensor is 22mm (0.022m) behind the physical front bumper
        self.front_distance = max(0.0, msg.data - 0.022)

        temp_msg = Twist()
        temp_msg.linear.x = self.last_raw_throttle
        self.sensor_control_adjust(temp_msg)
            
    def move_cmd_callback(self, msg: Twist):
        """Processes incoming joystick commands and saves them to state memory"""
        self.last_cmd_time = self.get_clock().now()
        self.safety_active = False

        # Save the intended forward/reverse throttle from the user
        self.last_raw_throttle = msg.linear.x

        # Steering processing (Direct passthrough with state delta verification)
        if msg.angular.z != self.last_steering:
            self.send_command(channel=2, value=msg.angular.z)
            self.last_steering = msg.angular.z

        # RESTORED: Instantly trigger the motor dispatch so the web UI feels snappy
        self.sensor_control_adjust(msg)

    def sensor_control_adjust(self, msg: Twist):
        """Dynamic Obstacle Avoidance: Enforces a 1.5-meter Deceleration Zone 
        where forward throttle is linearly clamped based on true bumper distance"""
        user_throttle = msg.linear.x
    
        # Only apply PID braking if driving forward and sensor is active
        if user_throttle > 0.0 and self.front_distance is not None:
            
            # 1. Calculate Time Delta (dt)
            current_time = self.get_clock().now()
            dt = (current_time - self.last_pid_time).nanoseconds / 1e9
            
            # 2. Calculate Proportional Error
            error = self.front_distance - self.target_distance
            
            # 3. TIME GUARD: Protect against double-triggers and stale start times
            if 0.01 < dt < 0.5:
                # Normal frame: Safe to calculate the derivative shock absorber
                self.integral_error += error * dt
                derivative = (error - self.last_error) / dt
            else:
                # Event happened too fast or car was parked for a long time. 
                # Bypass the derivative math to prevent -1.0 spikes!
                derivative = 0.0
                
            # 4. The PID Equation
            pid_output = (self.kp * error) + (self.ki * self.integral_error) + (self.kd * derivative)
            
            # Update state for the next loop
            self.last_error = error
            self.last_pid_time = current_time

            # --- DEAD-BAND MOTOR COMFORT ZONE ---
            # If the car arrives within 3cm of the target, force a quiet rest state
            if abs(error) < 0.03:
                pid_output = 0.0
                self.integral_error = 0.0
            
            # 5. Determine the final throttle
            adjusted_throttle = min(user_throttle, pid_output)
            
            # Clamp to the physical limits of your ESC (-1.0 to 1.0)
            adjusted_throttle = max(-1.0, min(1.0, adjusted_throttle))
            adjusted_throttle = round(adjusted_throttle, 2)

        else:
            # If reversing or no sensor data is active, bypass the loop entirely
            adjusted_throttle = round(user_throttle, 2)
                    
        # SPAM FILTER & COMMAND DISPATCH
        if adjusted_throttle != self.last_adjusted_throttle:

            # Dispatch the calculated throttle
            self.send_command(channel=0, value=adjusted_throttle)

            # Publish the states back to the UI Telemetry
            pub_msg = Twist()
            pub_msg.linear.x = float(adjusted_throttle)
            pub_msg.angular.z = float(self.last_steering)
            self.adjusted_publisher.publish(pub_msg)
            
            self.last_adjusted_throttle = adjusted_throttle

    def pid_tune_callback(self, msg: Vector3):
        """Dynamically updates the PID gains from the Web Interface"""
        self.kp = msg.x
        self.ki = msg.y
        self.kd = msg.z
        self.get_logger().info(f'Live Tune Applied -> Kp: {self.kp:.2f} | Ki: {self.ki:.2f} | Kd: {self.kd:.2f}')

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
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory


class ServoNode(Node):
    """
    Node responsible for controlling the steering servo (Futaba S3003).
    
    This node receives Twist commands from the Brain Node and converts
    the angular.z value into precise PWM signals to control the steering.
    """

    def __init__(self):
        super().__init__('servo_node')

        # Use hardware PWM (LGPIO) for stable and jitter-free servo control
        self.factory = LGPIOFactory()

        # Servo configuration
        self.PIN = 17                       # GPIO pin connected to servo signal wire
        self.MIN_PULSE = 0.0009             # 900 µs  → Full left
        self.MAX_PULSE = 0.0021             # 2100 µs → Full right

        self.servo = None
        self.init_servo() 

        # Subscribe to final steering commands from the Brain Node
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

        self.get_logger().info('Servo Node Started - Waiting for commands on /cmd_vel')

    def init_servo(self):
        """Initialize the steering servo with hardware PWM."""
        try:
            self.servo = Servo(
                pin=self.PIN,
                min_pulse_width=self.MIN_PULSE,
                max_pulse_width=self.MAX_PULSE,
                frame_width=0.020,                  # Standard 50Hz servo frequency
                pin_factory=self.factory
            )
            self.servo.value = 0.0
            self.get_logger().info(f'Servo successfully initialized on GPIO {self.PIN}')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize servo: {e}')
            self.servo = None

    def cmd_callback(self, msg: Twist):
        """
        Callback for incoming steering commands.
        Converts angular.z value (-1.0 to 1.0) into PWM signal for the servo.
        """
        steering = msg.angular.z

        if self.servo is None:
            self.get_logger().warn('Servo not initialized!')
            return

        # Safety clamp
        steering = max(-1.0, min(1.0, steering))
        self.servo.value = steering
        self.get_logger().debug(f'Servo command received: {steering:+.2f}')


def main(args=None):
    rclpy.init(args=args)
    node = ServoNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down servo node...')
    finally:
        # Return to center position on shutdown for safety
        if node.servo:
            node.servo.value = 0.0
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
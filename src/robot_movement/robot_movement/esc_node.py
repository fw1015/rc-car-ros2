import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory


class ESCNode(Node):
    """
    Node responsible for controlling the Electronic Speed Controller (ESC).
    
    This node receives Twist commands (primarily linear.x for throttle)
    and converts them into PWM signals to drive the brushed motor via the Tamiya TEU-104BK ESC.
    """

    def __init__(self):
        super().__init__('esc_node')

        # Use hardware PWM for more stable and accurate signal (important for ESC)
        self.factory = LGPIOFactory()

        # ESC configuration
        self.PIN = 18                       # GPIO pin connected to ESC signal wire
        self.MIN_PULSE = 0.0009             # 900 µs - Full reverse / minimum throttle
        self.MAX_PULSE = 0.0021             # 2100 µs - Full forward / maximum throttle

        self.esc = None
        self.init_esc()

        # Subscribe to final commands from the Brain Node
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

        self.get_logger().info('ESC Node Started - Waiting for commands on /cmd_vel')

    def init_esc(self):
        """Initialize the ESC with hardware PWM using gpiozero."""
        try:
            self.esc = Servo(
                pin=self.PIN,
                min_pulse_width=self.MIN_PULSE,
                max_pulse_width=self.MAX_PULSE,
                frame_width=0.020,                  # 50Hz standard servo/ESC frequency
                pin_factory=self.factory
            )
            self.esc.value = 0.0                    # Start at neutral
            self.get_logger().info(f'Servo successfully initialized on GPIO {self.PIN}')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize servo: {e}')
            self.esc = None

    def cmd_callback(self, msg: Twist):
        """
        Callback for incoming throttle commands from the Brain Node.
        Converts the linear.x value (-1.0 to 1.0) into PWM signal for the ESC.
        """
        throttle = msg.linear.x

        if self.esc is None:
            self.get_logger().warn('Esc not initialized!')
            return

        # Safety clamp
        throttle = max(-1.0, min(1.0, throttle))
        self.esc.value = throttle
        self.get_logger().debug(f'ESC command received: {throttle:+.2f}')


def main(args=None):
    rclpy.init(args=args)
    node = ESCNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down esc node...')
    finally:
        if node.esc:
            node.esc.value = 0.0
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
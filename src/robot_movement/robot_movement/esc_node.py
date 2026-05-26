import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory


class ESCNode(Node):
    def __init__(self):
        super().__init__('esc_node')

        # Hardware PWM for better stability
        self.factory = LGPIOFactory()

        self.PIN = 18
        self.MIN_PULSE = 0.0009
        self.MAX_PULSE = 0.0021

        self.esc = None
        self.init_esc()

        # Subscribe to commands from brain node
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

        self.get_logger().info('ESC Node Started - Waiting for commands on /cmd_vel')

    def init_esc(self):
        """Initialize ESC with hardware PWM"""
        try:
            self.esc = Servo(
                pin=self.PIN,
                min_pulse_width=self.MIN_PULSE,
                max_pulse_width=self.MAX_PULSE,
                frame_width=0.020,
                pin_factory=self.factory
            )
            self.esc.value = 0.0
            self.get_logger().info(f'Servo successfully initialized on GPIO {self.PIN}')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize servo: {e}')
            self.esc = None

    def cmd_callback(self, msg: Twist):
        """Receive throttle command"""
        throttle = msg.linear.x
        self.get_logger().info(f'Esc received: {throttle:+.2f}')

        if self.esc is None:
            self.get_logger().warn('Esc not initialized!')
            return

        # Safety clamp
        self.esc.value = throttle


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
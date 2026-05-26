import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Servo
from gpiozero.pins.lgpio import LGPIOFactory


class ServoNode(Node):
    def __init__(self):
        super().__init__('servo_node')

        # Hardware PWM for better stability
        self.factory = LGPIOFactory()

        self.PIN = 17
        self.MIN_PULSE = 0.0009
        self.MAX_PULSE = 0.0021

        self.servo = None
        self.init_servo() 

        # Subscribe to commands from brain node
        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_callback,
            10
        )

        self.get_logger().info('Servo Node Started - Waiting for commands on /cmd_vel')

    def init_servo(self):
        """Initialize servo with hardware PWM"""
        try:
            self.servo = Servo(
                pin=self.PIN,
                min_pulse_width=self.MIN_PULSE,
                max_pulse_width=self.MAX_PULSE,
                frame_width=0.020,
                pin_factory=self.factory
            )
            self.servo.value = 0.0
            self.get_logger().info(f'Servo successfully initialized on GPIO {self.PIN}')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize servo: {e}')
            self.servo = None

    def cmd_callback(self, msg: Twist):
        """Receive steering command"""
        steering = msg.angular.z
        self.get_logger().info(f'Servo received: {steering:+.2f}')

        if self.servo is None:
            self.get_logger().warn('Servo not initialized!')
            return

        # Safety clamp
        self.servo.value = steering


def main(args=None):
    rclpy.init(args=args)
    node = ServoNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down servo node...')
    finally:
        if node.servo:
            node.servo.value = 0.0
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
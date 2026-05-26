import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from gpiozero import DistanceSensor


class UltrasoundSensorNode(Node):
    """
    Node for reading left and right HC-SR04 ultrasonic sensors.

    Publishes distance data as ROS2 Range messages for use by the Brain Node.
    Currently only the left sensor is active (right is commented out for testing).
    """
    def __init__(self):
        super().__init__('ultrasound_sensor_node')

        # Publishers for left and right side distances
        self.pub_left = self.create_publisher(Range, '/left_distance', 10)
        self.pub_right = self.create_publisher(Range, '/right_distance', 10)

        # Initialize HC-SR04 sensors using gpiozero
        # Note: Echo pins must go through voltage divider (1kΩ+1kΩ) to 3.3V
        self.sensor_left = DistanceSensor(echo=22, trigger=27, max_distance=4.0)
        self.sensor_right = DistanceSensor(echo=24, trigger=23, max_distance=4.0)

        # Timer to publish distances at 5 Hz (every 200ms)
        self.timer = self.create_timer(0.2, self.publish_distances)

        self.get_logger().info("✅ Ultrasound Sensor Node Started (Left + Right)")

    def create_range_msg(self, distance_m: float, frame_id: str) -> Range:
        """
        Helper function to create a properly formatted Range message.
        """
        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = frame_id
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = 0.26        # ~15 degrees beam width
        msg.min_range = 0.02            # 2 cm minimum range
        msg.max_range = 4.0             # 4 meters maximum range
        msg.range = distance_m
        return msg

    def publish_distances(self):
        try:
            # Read distance in meters (gpiozero returns value in meters)
            dist_left = self.sensor_left.distance
            dist_right = self.sensor_right.distance

            # Create messages
            msg_left = self.create_range_msg(dist_left, "left_ultrasonic")
            msg_right = self.create_range_msg(dist_right, "right_ultrasonic")

            # Publish
            self.pub_left.publish(msg_left)
            self.pub_right.publish(msg_right)

            # Log in cm
            self.get_logger().info(
                f"L: {dist_left*100:5.1f}cm | R: {dist_right*100:5.1f}cm"
            )

        except Exception as e:
            self.get_logger().warning(f"Error reading ultrasonic sensors: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = UltrasoundSensorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Ultrasound Sensor Node...')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
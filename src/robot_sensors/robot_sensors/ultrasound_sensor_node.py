import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range
from gpiozero import DistanceSensor


class UltrasoundSensorNode(Node):
    def __init__(self):
        super().__init__('ultrasound_sensor_node')

        # Publishers
        self.pub_left = self.create_publisher(Range, '/left_distance', 10)
        # self.pub_right = self.create_publisher(Range, '/right_distance', 10)

        # Sensors
        self.sensor_left = DistanceSensor(echo=22, trigger=27, max_distance=4.0)
        # self.sensor_right = DistanceSensor(echo=24, trigger=23, max_distance=4.0)

        # Timer
        self.timer = self.create_timer(0.2, self.publish_distances)  # 5 Hz

        self.get_logger().info("✅ Ultrasound Sensor Node Started (Left + Right)")

    def create_range_msg(self, distance_m: float, frame_id: str) -> Range:
        """Helper to create a properly filled Range message"""
        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = frame_id
        msg.radiation_type = Range.ULTRASOUND
        msg.field_of_view = 0.26        # ~15 degrees
        msg.min_range = 0.02            # 2 cm
        msg.max_range = 4.0             # 4 meters
        msg.range = distance_m
        return msg

    def publish_distances(self):
        try:
            # Get distances in meters
            dist_left = self.sensor_left.distance
            # dist_right = self.sensor_right.distance

            # Create messages
            msg_left = self.create_range_msg(dist_left, "left_ultrasonic")
            # msg_right = self.create_range_msg(dist_right, "right_ultrasonic")

            # Publish
            self.pub_left.publish(msg_left)
            # self.pub_right.publish(msg_right)

            # Log (in cm for readability)
            self.get_logger().info(
                # f"L: {dist_left*100:5.1f}cm | R: {dist_right*100:5.1f}cm"
                f"L: {dist_left*100:5.1f}cm"
            )

        except Exception as e:
            self.get_logger().warning(f"Error reading sensors: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = UltrasoundSensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
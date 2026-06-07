import rclpy
import statistics
from collections import deque
from rclpy.node import Node
from sensor_msgs.msg import Range
from gpiozero import DistanceSensor


class UltrasoundSensorNode(Node):
    """
    Hardware driver node for side-facing HC-SR04 ultrasonic sensors.

    Responsibilities:
    - Interfaces with left and right HC-SR04 sensors via direct Pi GPIO.
    - Applies a rolling median temporal filter to eliminate acoustic noise and ghost echoes.
    - Publishes reliable distance data as standard ROS 2 Range messages.
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

        # Temporal Median Filter Memory
        # Keep track of the last 5 readings for each sensor
        self.left_history = deque(maxlen=5)
        self.right_history = deque(maxlen=5)

        # Polling Timer (5 Hz)
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
            # 1. Grab raw distance in meters
            raw_left = self.sensor_left.distance
            raw_right = self.sensor_right.distance

            # 2. Cull Out-of-Bounds Garbage Data
            # Only add to history if the reading is physically possible (2cm to 400cm)
            if 0.02 <= raw_left <= 4.0:
                self.left_history.append(raw_left)
                
            if 0.02 <= raw_right <= 4.0:
                self.right_history.append(raw_right)

            # 3. Process & Publish Independently (Prevents one dead sensor from halting both)
            if self.left_history and self.right_history:
                
                # Calculate the median of the last ~5 readings
                valid_left = statistics.median(self.left_history)
                valid_right = statistics.median(self.right_history)

                msg_left = self.create_range_msg(valid_left, "left_ultrasonic")
                msg_right = self.create_range_msg(valid_right, "right_ultrasonic")

                self.pub_left.publish(msg_left)
                self.pub_right.publish(msg_right)

                # Telemetry Logging
                self.get_logger().info(
                    f"L: {valid_left*100:5.1f}cm | R: {valid_right*100:5.1f}cm"
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
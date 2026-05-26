import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import time
import os
import vl53l5cx_ctypes as vl53l5cx

class TofSensorPublisher(Node):
    """
    Node for the VL53L5CX Time-of-Flight (ToF) sensor.
    
    This node reads distance data from the front-facing ToF sensor
    and publishes the minimum reliable distance as a Float64 message.
    """
    def __init__(self):
        super().__init__('tof_sensor_node')

        # Publisher for front distance (in meters)
        self.publisher = self.create_publisher(Float64, '/tof/distance', 10)
        
        self.tof = None
        self.init_sensor()

        # Timer to read sensor at 10Hz (every 100ms)
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.get_logger().info('ToF Sensor Node Started')

    def init_sensor(self):
        """Initialize the VL53L5CX sensor with 4x4 resolution."""
        try:
            self.tof = vl53l5cx.VL53L5CX()
            self.tof.set_resolution(4*4)
            self.tof.set_ranging_frequency_hz(10)
            self.tof.start_ranging()
            self.get_logger().info('VL53L5CX sensor initialized successfully')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize sensor: {e}')
            self.tof = None

    def distance_sensing(self):
        """Read the minimum reliable distance from the ToF sensor."""
        if self.tof is None:
            self.get_logger().warn('Sensor not initialized')
            return 4.0      # Return safe default (max range)
        
        try:
            if self.tof.data_ready():
                data = self.tof.get_data()
                distances = list(data.distance_mm[0])
                statuses = list(data.target_status[0])
                all_dist = []
                for row in range(4):    # 4x4 = 16 zones
                    row_values = []
                    for col in range(4):
                        idx = row * 4 + col
                        dist = distances[idx]
                        status = statuses[idx]
                        # Status 5 and 9 typically mean valid target detected
                        if status in (5, 9) and dist > 0:
                            all_dist.append(dist)
                
                if all_dist:
                    min_dist_mm = min(all_dist)
                    min_dist_m = min_dist_mm/1000       # Convert to meters
                    return min_dist_m
                else:
                    self.get_logger().warn('No valid distance readings')
                    return 4.0
            else:
                return 4.0  # No new data available yet
        
        except Exception as e:
            self.get_logger().error(f'Error reading sensor: {e}')
            return 4.0


    def timer_callback(self):
        """Timer callback to periodically publish distance."""
        distance = self.distance_sensing()

        # Safety clamp: keep distance between 0.02m and 4.0m
        distance = max(0.02, min(4.0, distance))
        msg = Float64()
        msg.data = distance
        self.publisher.publish(msg)

        # Optional debug logging (uncomment when needed)
        # if distance < 0.4:
        #     self.get_logger().warn(f'⚠️ Close obstacle detected: {distance:.2f}m')
        # else:
        #     self.get_logger().debug(f'Front distance: {distance:.2f}m')

def main(args=None):
    rclpy.init(args=args)
    node = TofSensorPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down ToF Sensor Node...')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

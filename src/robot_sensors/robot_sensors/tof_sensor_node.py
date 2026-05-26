import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import time
import os
import vl53l5cx_ctypes as vl53l5cx

class TofSensorPublisher(Node):
    def __init__(self):
        super().__init__('tof_sensor_node')
        self.publisher = self.create_publisher(Float64, '/tof/distance', 10)
        
        self.tof = None
        self.init_sensor()
        self.get_logger().info('ToF Sensor Node Started')
        self.timer = self.create_timer(0.1, self.timer_callback)

    def init_sensor(self):
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
        if self.tof is None:
            self.get_logger().warn('Sensor not initialized')
            return 4.0
        
        try:
            if self.tof.data_ready():
                data = self.tof.get_data()
                distances = list(data.distance_mm[0])
                statuses = list(data.target_status[0])
                all_dist = []
                for row in range(4):
                    row_values = []
                    for col in range(4):
                        idx = row * 4 + col
                        dist = distances[idx]
                        status = statuses[idx]
                        if status in (5, 9) and dist > 0:
                            all_dist.append(dist)
                
                if all_dist:
                    min_dist_mm = min(all_dist)
                    min_dist_m = min_dist_mm/1000
                    return min_dist_m
                else:
                    self.get_logger().warn('No valid distance readings')
                    return 4.0
            else:
                return 4.0
        
        except Exception as e:
            self.get_logger().error(f'Error reading sensor: {e}')
            return 4.0


    def timer_callback(self):
        distance = self.distance_sensing()
        distance = max(0.02, min(4.0, distance))
        msg = Float64()
        msg.data = distance
        self.publisher.publish(msg)
        # if distance < 0.3:
        #     self.get_logger().warn(f'⚠️ Obstacle at {distance:.3f}m')
        # else:
        #     self.get_logger().info(f'Distance: {distance:.3f}m')

def main(args=None):
    rclpy.init(args=args)
    node = TofSensorPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import vl53l5cx_ctypes as vl53l5cx

class TofSensorPublisher(Node):
    """
    Hardware driver node for the VL53L5CX Time-of-Flight sensor
    
    Responsibilities:
    - Initializes the I2C ToF sensor in 4x4 grid resolution mode
    - Polls the hardware synchronously at 10Hz
    - Applies spatial clustering (neighbor check) to the center 4 zones to filter noise
    - Publishes the final reliable distance in meters to the `/tof/distance` topic
    """

    def __init__(self):
        super().__init__('tof_sensor_node')

        self.publisher = self.create_publisher(Float64, '/tof/distance', 10)
        
        # Hardware State
        self.tof = None
        self.init_tof_sensor()

        # Timer to read the sensor at 10 Hz
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.get_logger().info('ToF Sensor Node started (Standalone)')

    def init_tof_sensor(self):
        """Attempts to initialize the VL53L5CX sensor over I2C"""
        try:
            self.tof = vl53l5cx.VL53L5CX()
            self.tof.set_resolution(4*4)
            self.tof.set_ranging_frequency_hz(10)
            self.tof.start_ranging()
            self.get_logger().info("✅ VL53L5CX initialized successfully")
        except Exception as e:
            self.get_logger().error(f"Failed to init ToF sensor: {e}")
            self.tof = None

    def timer_callback(self):
        """Main sensor polling loop. Retrieves the raw 4x4 distance grid, isolates 
        the forward-facing path, applies noise filtering, and publishes the result"""
        # Publish safe default (4.0m) if the sensor hardware is dead or disconnected
        if self.tof is None:
            msg = Float64()
            msg.data = 4.0
            self.publisher.publish(msg)
            return

        try:
            if self.tof.data_ready():
                data = self.tof.get_data()
                distances = list(data.distance_mm[0])
                statuses = list(data.target_status[0])
                
                # 1. Isolate the center 4 zones of the 4x4 grid
                # Indices 5, 6, 9, 10 form the exact physical center of the FOV
                center_zones = [5, 6, 9, 10]
                center_dists = {}

                for i in center_zones:
                    # Statuses 5 and 9 are VL53L5CX hardware codes for "Range Valid"
                    if statuses[i] in (5, 9) and distances[i] > 0:
                        center_dists[i] = distances[i]

                valid_obstacle_dists = []

                # 2. Spatial Clustering: The "Neighbor Check"
                # To prevent phantom braking from stray reflections, a distance point is 
                # only considered valid if an adjacent zone agrees within 150mm (15cm)
                for zone_index, dist in center_dists.items():
                    has_neighbor = any(
                        abs(dist - other_dist) < 150 
                        for other_index, other_dist in center_dists.items() 
                        if other_index != zone_index
                    )
                    if has_neighbor:
                        valid_obstacle_dists.append(dist)

                # 3. Calculate Final Safe Distance and Publish
                msg = Float64()
                if valid_obstacle_dists:
                    # Return the closest verified threat, converted from mm to meters
                    msg.data = min(valid_obstacle_dists) / 1000.0
                else:
                    msg.data = 4.0
                    
                self.publisher.publish(msg)

        except Exception as e:
            self.get_logger().warning(f"Error reading ToF: {e}")
            # Failsafe on I/O error
            msg = Float64()
            msg.data = 4.0
            self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TofSensorPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
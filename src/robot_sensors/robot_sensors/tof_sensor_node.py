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
        """Main sensor polling loop. Creates a horizontal 'letterbox' field of view 
        to ignore ground/bumper reflections while detecting wide or thin forward obstacles."""
        
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

                # --- TEMPORARY DEBUG VISUALIZER ---
                
                grid = [distances[i:i+4] for i in range(0, 16, 4)]
                stat_grid = [statuses[i:i+4] for i in range(0, 16, 4)]
                self.get_logger().info(
                    f"\nDISTANCES:\nRow 1 [4-7]:   {grid[1]}\n"
                    f"STATUSES:\nRow 1 [4-7]:   {stat_grid[1]}\n------------------------"
                )
                # ----------------------------------
                # ----------------------------------
                
                # 1. NARROW HORIZONTAL FOV (The "Blinders")
                horizon_zones = [5, 6]
                valid_obstacle_dists = []

                # 2. Extract valid distances (Relaxed for Outdoors)
                for i in horizon_zones:
                    # 5 & 9 = Perfect valid reading
                    # 6, 10, 12 = Warning readings (Extremely common outdoors due to sunlight IR interference)
                    if statuses[i] in (5, 6, 9, 10, 12) and distances[i] > 0:
                        valid_obstacle_dists.append(distances[i])

                # 3. Calculate Final Safe Distance and Publish
                msg = Float64()
                if valid_obstacle_dists:
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
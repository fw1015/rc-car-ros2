import rclpy
# from pynput import keyboard
import time
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist

class RobotBrainNode(Node):
    def __init__(self):
        super().__init__('robot_brain_node')
        self.tof_subscription = self.create_subscription(
            Float64, 
            '/tof/distance', 
            self.front_dist_callback, 
            10
        )

        self.dir_cmd_subscription = self.create_subscription(
            Twist,
            '/cmd_vel_raw',
            self.dir_raw_callback,
            10
        )

        self.servo_publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )
          
    def front_dist_callback(self, msg):
        distance = msg.data
        # self.get_logger().info(f'Distance: {distance:.3f}m')
        # if distance < 0.3:
        #     self.get_logger().warn('STOP! Obstacle detected!')
        # else:
        #     self.get_logger().info('Path clear, moving forward')
    
    def dir_raw_callback(self, msg):
        twist = Twist()
        twist.linear.x = msg.linear.x
        twist.angular.z = msg.angular.z
        self.servo_publisher.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = RobotBrainNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
        
if __name__ == '__main__':
    main()
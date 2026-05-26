import rclpy
import time
from rclpy.node import Node
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist

class RobotBrainNode(Node):
    """
    Central decision-making node for the RC Car.
    
    This node acts as the 'brain':
    - Receives raw commands from the web interface
    - Receives sensor data (ToF distance)
    - Can apply safety logic / obstacle avoidance in the future
    - Forwards final safe commands to the movement nodes
    """

    def __init__(self):
        super().__init__('robot_brain_node')

        # Subscription to ToF distance sensor (for future obstacle avoidance)
        self.tof_subscription = self.create_subscription(
            Float64, 
            '/tof/distance', 
            self.front_dist_callback, 
            10
        )

        # Subscription to raw commands coming from the web interface
        self.dir_cmd_subscription = self.create_subscription(
            Twist,
            '/cmd_vel_raw',
            self.dir_raw_callback,
            10
        )

        # Publisher to send final commands to servo and ESC nodes
        self.servo_publisher = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.get_logger().info('Robot Brain Node has been started')
          
    def front_dist_callback(self, msg):
        """Process front distance data from ToF sensor."""
        distance = msg.data
        # Future obstacle avoidance logic can be added here
        # Example:
        # if distance < 0.3:
        #     self.get_logger().warn(f'Obstacle detected! Distance: {distance:.2f}m')
        #     self.emergency_stop()
        
        # Currently just logging for debugging
        # self.get_logger().info(f'Front distance: {distance:.3f} m')
    
    def dir_raw_callback(self, msg):
        """
        Receives raw Twist commands from the web interface and forwards them.
        
        In the future, this is where safety logic (speed limiting, 
        obstacle avoidance, etc.) will be applied before sending 
        final commands to the hardware nodes.
        """
        # For now, simply forward the command
        # In later versions add filtering and safety checks here
        twist = Twist()
        twist.linear.x = msg.linear.x
        twist.angular.z = msg.angular.z
        self.servo_publisher.publish(twist)
    
    # Optional: Future helper method
    # def emergency_stop(self):
    #     stop_msg = Twist()
    #     stop_msg.linear.x = 0.0
    #     stop_msg.angular.z = 0.0
    #     self.servo_publisher.publish(stop_msg)
    #     self.get_logger().warn("Emergency Stop Activated!")

def main(args=None):
    rclpy.init(args=args)
    node = RobotBrainNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down Robot Brain Node...')
    finally:
        node.destroy_node()
        rclpy.shutdown()
        
if __name__ == '__main__':
    main()
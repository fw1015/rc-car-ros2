#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
import time
from adafruit_extended_bus import ExtendedI2C as I2C
from adafruit_pca9685 import PCA9685 

# Note: We completely removed the ToF / GetDistance imports!
from robot_movement.srv import SetESCServo

class I2CManager(Node):
    """
    Dedicated Motor Controller Node.
    
    Handles the PCA9685 PWM driver over I2C to control the ESC (Throttle) 
    and Servo (Steering) via ROS 2 service calls.
    """

    def __init__(self):
        super().__init__('i2c_manager')
        
        self.get_logger().info("Starting I2C Manager (Motor Control Only)...")

        # Initialize I2C Bus 2
        self.i2c_esc = I2C(2)
        time.sleep(0.5)

        # Initialize ROS 2 Service before hardware to prevent missing-service warnings
        self.create_service(SetESCServo, 'set_esc_servo', self.set_esc_servo_callback)

        # PCA9685 Hardware State
        self.pca = None
        self.esc_initialized = False

        # Hardware connection retry loop (executes every 2 seconds until powered)
        self.esc_retry_timer = self.create_timer(2.0, self.try_init_esc_servo)
        self.get_logger().info("I2C Manager started. Waiting for ESC power if needed.")

    def _set_pwm_pulse(self, channel, pulse_us):
        """
        Safely converts a microsecond pulse into a 16-bit hardware duty cycle.
        
        Args:
            channel (int): The PCA9685 channel (0-15).
            pulse_us (float): The desired PWM pulse width in microseconds.
        """
        if self.pca is None:
            return
            
        # Hardware safety clamp: Prevent sending signals outside standard RC limits
        pulse_us = max(900, min(2100, pulse_us))
        
        # Convert microsecond pulse to 16-bit duty cycle at 50Hz (20,000us period)
        duty = int((pulse_us / 20000) * 65535)
        self.pca.channels[channel].duty_cycle = duty

    def try_init_esc_servo(self):
        """Attempts to connect to the PCA9685 and arm the motors."""
        if self.esc_initialized:
            return
            
        try:
            # Initialize bare-metal chip
            self.pca = PCA9685(self.i2c_esc)
            self.pca.frequency = 50  # Must be exactly 50Hz for standard RC equipment
            
            # CHANNEL 0: Arm the ESC (1500us Neutral)
            self._set_pwm_pulse(0, 1500) # Neutral 1500us
            
            # CHANNEL 2: Center the Steering Servo (1500us Neutral)
            self._set_pwm_pulse(2, 1500) # Center 1500us
            
            self.esc_initialized = True
            self.get_logger().info("✅ PCA9685 initialized: ESC Armed & Wheels Centered!")
            
            # Terminate the retry loop upon successful connection
            self.esc_retry_timer.cancel()
            
        except Exception as e:
            self.get_logger().warn(f"PCA9685 not ready yet: {e}")

    def set_esc_servo_callback(self, request, response):
        """
        Service callback to actuate physical hardware.
        Maps incoming float values (-1.0 to 1.0) to physical PWM microseconds.
        """
        if not self.esc_initialized or self.pca is None:
            response.success = False
            response.message = "PCA9685 not powered on yet"
            return response
            
        try:
            channel = request.channel
            value = request.value  # Value arrives as -1.0 to 1.0
            
            if channel == 0:
                # CHANNEL 0: ESC (Throttle)
                # Mapping: -1.0 -> 1000us | 0.0 -> 1500us | 1.0 -> 2000us
                pulse = 1500 + (value * 500)
                self._set_pwm_pulse(0, pulse)
                response.message = f"ESC throttle set to {value:.2f} ({pulse}us)"
                
            elif channel == 2:
                # CHANNEL 2: STEERING SERVO
                # Mapping: -1.0 -> 900us | 0.0 -> 1500us | 1.0 -> 2100us
                pulse = 1500 + (value * 600)
                self._set_pwm_pulse(2, pulse)
                response.message = f"Servo steering set to {value:.2f} ({pulse}us)"
            
            response.success = True
            
        except Exception as e:
            response.success = False
            response.message = str(e)
            
        return response


def main():
    rclpy.init()
    node = I2CManager()
    
    # Utilizing MultiThreadedExecutor to maintain high responsiveness for service calls
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
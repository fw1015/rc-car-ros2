# Hardware Architecture & Node Mapping

This document outlines the hardware components and their corresponding ROS2 nodes.

## Node Overview

| Node                  | Hardware? | Model                        | Power     | Key Pins                                      | Placement   | Publishes                     | Subscribes                      | Message Type       |
|-----------------------|-----------|------------------------------|-----------|-----------------------------------------------|-------------|-------------------------------|---------------------------------|--------------------|
| `robot_brain_node`    | No        | -                            | -         | -                                             | -           | `/cmd_vel`                    | `/tof/distance`, `/cmd_vel_raw` | `Twist`, `Float64` |
| `tof_sensor_node`     | Yes       | VL53L5CX (ToF)               | 3.3V      | SDA (GPIO2), SCL (GPIO3), Power               | Front       | `/tof/distance`               | -                               | `Float64`          |
| `us_sensor_node (L)`  | Yes       | HC-SR04                      | 5V        | Trig (GPIO27), Echo (GPIO22)                  | Left Side   | `/left_distance`              | -                               | `Range`            |
| `us_sensor_node (R)`  | Yes       | HC-SR04                      | 5V        | Trig (GPIO23), Echo (GPIO24)                  | Right Side  | `/right_distance`             | -                               | `Range`            |
| `servo_node`          | Yes       | Futaba S3003                 | 5V        | Signal (GPIO17)                               | Internal    | -                             | `/cmd_vel`                      | `Twist`            |
| `esc_node`            | Yes       | Tamiya TEU-104BK             | 7.2V      | PWM Signal (GPIO18)                           | Internal    | -                             | `/cmd_vel`                      | `Twist`            |
| `camera_ros`          | Yes       | Raspberry Pi Camera Module 3 Wide | 5V (via Pi) | CSI Port (Ribbon Cable)                    | Front       | `/camera/image_raw/compressed`| -                               | `CompressedImage`  |
| `web_server_node`     | No        | Flask + Socket               | -         | -                                             | -           | `/cmd_vel_raw`                | Sensors                         | `Twist`            |
| `TXS0108E`            | Yes       | Level Shifter                | 3.3V/5V   | VA=3.3V, VB=5V                                | Internal    | -                             | -                               | -                  |

## Power Architecture

- **Main Battery (7.2V NiMH)**: Powers ESC directly + Servo (via UBEC in future)
- **Pi 5V Rail**: Powers Raspberry Pi, Camera Module 3, and HC-SR04 sensors
- **Pi 3.3V Rail**: Powers logic level (ToF sensor, TXS0108E VA)
- **Common Ground**: All components share the same ground

## Notes

- HC-SR04 Echo pins use voltage divider (1kΩ + 1kΩ) to step down 5V → 3.3V.
- Camera uses the official CSI port on the Pi 5.
- Future improvement: Dedicated 5V UBEC + better power distribution board.

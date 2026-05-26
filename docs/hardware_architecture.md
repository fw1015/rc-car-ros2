# Hardware Architecture & Node Mapping

This document outlines the hardware components and their corresponding ROS2 nodes.

## Node Overview

| Node                  | Hardware? | Model                  | Power     | Key Pins                          | Placement   | Publishes                  | Subscribes                      | Message Type       |
|-----------------------|-----------|------------------------|-----------|-----------------------------------|-------------|----------------------------|---------------------------------|--------------------|
| `robot_brain_node`    | No        | -                      | -         | -                                 | -           | `/cmd_vel`                 | `/tof/distance`, `/cmd_vel_raw` | `Twist`, `Float64` |
| `tof_sensor_node`     | Yes       | VL53L5CX (ToF)         | 3.3V      | SDA (GPIO2), SCL (GPIO3), Power   | Front       | `/tof/distance`            | -                               | `Float64`          |
| `us_sensor_node (L)`  | Yes       | HC-SR04                | 5V        | Trig (GPIO27), Echo (GPIO22)      | Left Side   | `/left_distance`           | -                               | `Range`            |
| `us_sensor_node (R)`  | Yes       | HC-SR04                | 5V        | Trig (GPIO23), Echo (GPIO24)      | Right Side  | `/right_distance`          | -                               | `Range`            |
| `servo_node`          | Yes       | Futaba S3003           | 5V        | Signal (GPIO17)                   | Internal    | -                          | `/cmd_vel`                      | `Twist`            |
| `esc_node`            | Yes       | Tamiya TEU-104BK       | 7.2V      | PWM Signal (GPIO18)               | Internal    | -                          | `/cmd_vel`                      | `Twist`            |
| `web_server_node`     | No        | Flask + Socket         | -         | -                                 | -           | `/cmd_vel_raw`             | Sensors                         | `Twist`            |
| `TXS0108E`            | Yes       | Level Shifter          | 3.3V/5V   | VA=3.3V, VB=5V                    | Internal    | -                          | -                               | -                  |

## Power Architecture

- **Main Battery (7.2V NiMH)**: Powers Servo & ESC directly
- **Pi 3.3V**: Powers logic and ToF sensor

## Notes

- Echo pins from HC-SR04 use voltage divider (1kΩ + 1kΩ) to step down to 3.3V.
- All grounds are common.
- Future improvement: Dedicated power distribution board.

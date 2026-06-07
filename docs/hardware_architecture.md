# Hardware Architecture & Node Mapping

This document outlines the hardware components and their corresponding ROS2 nodes.

## Node Overview

| Node | Hardware? (Y/N) | Model | PIN Required | Placement | Publish | Subscriber | Message Type | Service/Client |
|------|-----------------|-------|--------------|-----------|---------|------------|--------------|----------------|
| `robot_brain_node` | N | NA | NA | NA | 1. `/cmd_vel` | 1. `/tof/distance`<br>2. `/cmd_vel_raw` | 1. `Float64`<br>2. `Twist` | Client to `i2c_manager` |
| `tof_sensor_node` | Y | VL53L5CX | PIN 1 - 3V3 Power <=> LPn, PWREN, AVDD, IOVDD<br>PIN 3 - GPIO 2 (SDA) <=> SDA<br>PIN 5 - GPIO 3 (SCL) <=> SCL<br>PIN 9 - GND <=> GND | Front | 1. `/tof/distance` | | `Float64` | |
| `us_sensor_node (L)` | Y | HC-SR04 | PIN 2 - 5V Power <=> VCC<br>PIN 9 - GND <=> GND<br>PIN 13 - GPIO 27 <=> Trig<br>PIN 15 - GPIO 22 <=> Echo | Side | 1. `/left_distance` | | | |
| `us_sensor_node (R)` | Y | HC-SR04 | PIN 4 - 5V Power <=> VCC<br>PIN 9 - GND <=> GND<br>PIN 16 - GPIO 23 <=> Trig<br>PIN 18 - GPIO 24 <=> Echo | Side | 1. `/right_distance` | | | |
| `i2c_manager` | Y | Futaba 53003 (Servo)<br>QUICRUN-1060 (ESC)<br>PCA9685 | 3PINS <=> PCA Channel 2<br>3PINS <=> PCA Channel 0<br>PIN 7 - GPIO 4 (SDA) <=> i2c bus2 SDA<br>PIN 29 - GPIO 5 (SCL) <=> i2c bus2 SCL<br>PIN 17 3V3 Power <=> VCC<br>ESC Signal <=> Channel 0<br>PIN 34 - GND <=> OE<br>PIN 39 - GND <=> GND | Mid | | | | Service to `robot_brain_node` |
| `web_server_node` | N | NA | NA | NA | 1. `/cmd_vel_raw` | 1. `/tof/distance`<br>2. `/left_distance`<br>3. `/right_distance` | | |

## Power Architecture

- **Main Battery (7.2V NiMH)**: Powers the ESC directly.
- **ESC Built-in BEC (6V/3A)**: The QUICRUN 1060 ESC automatically steps down the battery voltage and powers the PCA9685 V+ rail, which safely drives the Futaba S3003 Steering Servo.
- **Pi 5V Rail**: Powers the Raspberry Pi, Camera Module 3, and HC-SR04 ultrasonic sensors.
- **Pi 3.3V Rail**: Powers logic level components (VL53L5CX ToF sensor and PCA9685 VCC logic).
- **Common Ground**: All components (Pi, Sensors, PCA9685, ESC) share a common ground to prevent signal floating.

## Notes

- HC-SR04 Echo pins use a voltage divider (1kΩ + 1kΩ) to safely step down the 5V return signal to 2.5V, which registers as a safe logic HIGH for the Pi's 3.3V GPIO pins.
- The Camera stream utilizes the official CSI ribbon port on the Pi 5 to free up USB bandwidth.
- The I2C PCA9685 board successfully isolates the 3.3V Pi logic from the 6V servo power rail.

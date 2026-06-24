# Hardware Architecture & Node Mapping

This document outlines the hardware components, their corresponding ROS 2 nodes, and the physical wiring architecture of the autonomous RC vehicle.

## Node Overview

| Node                  | Hardware? | Model                  | Placement | Publish                  | Subscribe                          | Message Type       | Service/Client          |
|-----------------------|-----------|------------------------|-----------|--------------------------|------------------------------------|--------------------|-------------------------|
| `robot_brain_node`    | N         | NA                     | NA        | `/cmd_vel`               | `/tof/distance`, `/cmd_vel_raw`    | `Twist`, `Float64` | Client to `i2c_manager` |
| `tof_sensor_node`     | Y         | VL53L5CX               | Front     | `/tof/distance`          | -                                  | `Float64`          | -                       |
| `us_sensor_node (L)`  | Y         | HC-SR04                | Left      | `/left_distance`         | -                                  | `Range`            | -                       |
| `us_sensor_node (R)`  | Y         | HC-SR04                | Right     | `/right_distance`        | -                                  | `Range`            | -                       |
| `i2c_manager`         | Y         | PCA9685 + QUICRUN-1060 | Mid       | -                        | -                                  | -                  | Service (`set_esc`)     |
| `web_server_node`     | N         | NA                     | NA        | `/cmd_vel_raw`           | `/tof/distance`, `/left_distance`, `/right_distance` | `Twist` | - |

---

## Hardware Components

### USB WiFi Adapter (TP-Link Archer T3U Plus)

- **Model**: TP-Link Archer T3U Plus (AC1300)
- **Purpose**: Provides stable, longer-range WiFi connectivity for outdoor operation and reliable live camera streaming.
- **Connection Type**: USB 3.0 (plugged into Raspberry Pi 5 USB port)
- **Usage**:
  - Acts as WiFi **client** when connecting to a phone hotspot in Field Mode.
  - Improves stability and range compared to the built-in Raspberry Pi WiFi, especially outdoors.
- **Power Consumption**: ~500–900mA under load (powered directly from Pi USB 3.0 port).
- **Notes**: 
  - Used primarily to maintain a stable connection for camera streaming when operating away from home WiFi.
  - Helps reduce latency and dropouts during outdoor testing.

### VL53L5CX (ToF Sensor)
- **PIN 1 (3V3 Power)**: LPn, PWREN, AVDD, IOVDD
- **PIN 3 (GPIO 2)**: SDA
- **PIN 5 (GPIO 3)**: SCL
- **PIN 9 (GND)**: GND

### HC-SR04 (Left Ultrasonic)
- **PIN 2 (5V Power)**: VCC
- **PIN 9 (GND)**: GND
- **PIN 13 (GPIO 27)**: Trig
- **PIN 15 (GPIO 22)**: Echo

### HC-SR04 (Right Ultrasonic)
- **PIN 4 (5V Power)**: VCC
- **PIN 9 (GND)**: GND
- **PIN 16 (GPIO 23)**: Trig
- **PIN 18 (GPIO 24)**: Echo

### PCA9685 (I2C Motor Manager)
- **PIN 17 (3V3 Power)**: VCC (logic)
- **PIN 34 & 39 (GND)**: GND + OE
- **Channel 0**: QUICRUN-1060 ESC (Throttle)
- **Channel 2**: Futaba S3003 Servo (Steering)

---

## Power Architecture

- **Main Battery (7.2V NiMH)**: Powers the ESC directly.
- **ESC Built-in BEC (6V/3A)**: Powers the PCA9685 V+ rail → Futaba S3003 steering servo.
- **Pi 5V Rail**: Powers the Raspberry Pi, **TP-Link Archer T3U Plus**, Camera Module 3, and both HC-SR04 sensors.
- **Pi 3.3V Rail**: Powers the VL53L5CX ToF sensor and PCA9685 logic (VCC).
- **Common Ground**: All components share a common ground to ensure signal integrity.

**Note on USB WiFi Adapter**: The TP-Link Archer T3U Plus draws power from the Pi’s USB 3.0 port. While the Pi 5 can generally handle it, high camera streaming load + USB WiFi may increase total current draw. Monitor thermals during long outdoor sessions.

---

## Notes

- HC-SR04 Echo pins use a voltage divider (1kΩ + 1kΩ) to safely step down 5V signals to 3.3V logic levels.
- The **TP-Link Archer T3U Plus** was added specifically to improve WiFi stability and camera streaming performance when operating outdoors in Field Mode.
- The Camera Module 3 uses the official CSI port to avoid USB bandwidth contention with the WiFi adapter.
- The PCA9685 provides electrical isolation between the Pi’s 3.3V logic and the higher voltage servo/ESC power rail.
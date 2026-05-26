# RC Car ROS2 Project

An autonomous RC car built with **ROS 2 Jazzy**, **Raspberry Pi 5**, and a web-based control interface.

![Project Status](https://img.shields.io/badge/Status-In%20Development-yellow)
![ROS2](https://img.shields.io/badge/ROS2-Jazzy-blue)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-5-green)

## Features

- **Real-time Web Control** — Control steering and throttle via browser (phone-friendly)
- **Live Camera Streaming** — Stream video from Raspberry Pi Camera Module 3
- **Multi-Sensor System** — VL53L5CX (ToF) + dual HC-SR04 ultrasonic sensors
- **Field Mode** — Built-in WiFi hotspot for outdoor operation (no home router needed)
- **ROS2 Architecture** — Web Server Node, Brain Node, Sensors Node, Movement Node
- **3D Printed Mounts** — Custom fixtures for Pi, camera, and sensors

## Tech Stack

- **ROS 2 Jazzy** (Ubuntu 24.04)
- **Raspberry Pi 5** + Camera Module 3 Wide
- **Python** + Flask (web interface)
- **gpiozero** + LGPIO (hardware control)
- **SolidWorks** (3D design)

## Project Structure
src/
├── web_interface/          # Flask web server + frontend
├── robot_brain/            # Decision making node
├── robot_movement/         # Servo and ESC control
├── robot_sensors/          # ToF + Ultrasonic sensors
└── camera_ros/             # Camera node for live feed

## How to Run
```bash
cd ~/ros2_robot_ws
source install/setup.bash

# Run full system
ros2 launch web_interface web_control.launch.py

cmake_minimum_required(VERSION 3.8)
project(robot_movement)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# 1. Build the custom services (This automatically sets up the Python package target!)
rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SetESCServo.srv"
)

# 2. Install the executables and strip the .py extension
install(PROGRAMS robot_movement/servo_node.py
        DESTINATION lib/${PROJECT_NAME}
        RENAME servo_node)

install(PROGRAMS robot_movement/i2c_manager.py
        DESTINATION lib/${PROJECT_NAME}
        RENAME i2c_manager)

ament_package()
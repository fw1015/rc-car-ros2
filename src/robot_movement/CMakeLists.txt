cmake_minimum_required(VERSION 3.8)
project(robot_movement)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Build the custom services
rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SetESCServo.srv"
)

# Install the executables
install(PROGRAMS robot_movement/i2c_manager.py
        DESTINATION lib/${PROJECT_NAME}
        RENAME i2c_manager)

ament_package()
#!/bin/bash
echo "=== SWITCHING TO FIELD/HOTSPOT MODE ==="

# 1. Bring up the hotspot (WITH PASSWORDLESS SUDO)
echo "Starting high-speed hotspot on the external antenna..."
sudo nmcli connection up "Hotspot-4"

# 2. Verify the network hardware is actually broadcasting
echo "Verifying hotspot is active..."
for i in {1..10}; do
    if nmcli connection show --active | grep -q "Hotspot-4"; then
        echo "✅ Hotspot is LIVE! Proceeding to launch..."
        break
    fi
    echo "Waiting for hotspot to stabilize... attempt $i/10"
    sleep 2
    
    # If we reach attempt 10 and it still isn't up, safely abort
    if [ "$i" -eq 10 ]; then
        echo "❌ CRITICAL ERROR: Hotspot failed to start. Aborting launch."
        exit 1
    fi
done

# 3. Source the Base ROS 2 Environment
source /opt/ros/humble/setup.bash

# 4. Navigate and source the workspace
cd /home/fwann/Documents/Project/ros2_robot_ws
source install/setup.bash

# 5. Launch the robot!
echo "Launching all nodes..."
exec ros2 launch web_interface web_control.launch.py
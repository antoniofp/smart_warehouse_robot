import os
import subprocess

driver_file = "/root/yahboomcar_ros2_ws/yahboomcar_ws/src/yahboomcar_bringup/yahboomcar_bringup/Ackman_driver_R2.py"
print(f"Patching {driver_file}")

with open(driver_file, "r") as f:
    content = f.read()

# Replace twist.linear.y = vy*1000*1.0 with twist.linear.y = vy*180.0/3.1416
new_content = content.replace("twist.linear.y = vy*1000*1.0   #steer angle", "twist.linear.y = vy * 180.0 / 3.14159265   #steer angle in degrees")

if new_content == content:
    print("Warning: Could not find the target string to replace.")
else:
    with open(driver_file, "w") as f:
        f.write(new_content)
    print("Successfully patched driver scaling!")


📸 DIY Photogrammetry Station (Scrap-Built 3D Scanner)
An automated, IoT-based 3D scanning solution built with recycled scanner parts and 3D printed components. This station uses an ESP32 and Python to synchronize a turntable and a vertical elevator for high-quality photogrammetry.

✨ Features
Fully Automated: Synchronized movement between the turntable (rotation) and elevator (Z-axis).

IoT Control: Web-based interface to monitor and control the scan from any device.

Smartphone Integration: Uses your phone's camera via a browser-based stream.

High-Torque Drive: Custom firmware logic to get maximum power from small stepper motors.

Smart Cropping: Real-time "Crop Box" selection to save only the subject.

🛠 Hardware & Recycling (BOM)
This project is a "Scrap-Build," meaning it's designed to use parts from old office equipment.

Recycled Parts: 2x Linear rods and bushings (salvaged from an old paper scanner).

Z-Axis Drive: Continuous timing belt system with 3D printed gear reduction.

Motors: 2x 28BYJ-48 Stepper Motors with ULN2003 drivers.

Tilt Control: 1x MG996R Servo motor for camera angle adjustment.

Brain: ESP32-S3 (or standard ESP32).

Power: External 5V 3A DC power supply (Mandatory).

Note: Since linear rods vary, you may need to adjust the hole diameters in your slicer to fit your specific rods.

🔌 Wiring Guide (Pinout)
Turntable Motor: Pins 8, 9, 10, 11

Elevator Motor: Pins 6, 5, 7, 4

Servo Motor: Pin 3 (Signal)

Power: GND (Common Ground)

🚀 Installation & Setup
1. ESP32 Firmware
Open v_2_2.ino in Arduino IDE.

Enter your Wi-Fi SSID and Password.

Upload the code and note the IP address.

2. Python Server
Install dependencies: pip install flask flask-socketio requests pillow

Update ayarlar.json with your ESP32's IP address.

Run baslat.bat or python app.py.

3. Start Scanning
Open phone browser: https://[YOUR_PC_IP]:5000

Open PC browser: http://localhost:5000/monitor

Set your crop area and hit START!

📜 License
This project is licensed under CC BY-NC (Creative Commons Attribution-NonCommercial).

# 📸 DIY Photogrammetry Station (Scrap-Built)

An automated, IoT-based 3D scanning solution built with recycled scanner parts. This station uses an **ESP32** and **Python** to synchronize a turntable and a vertical elevator.

---

## ✨ Features

* **Fully Automated:** Synchronized movement between turntable and Z-axis.
* **IoT Control:** Web interface to control the scan from any device.
* **Smartphone Integration:** Uses your phone's camera via a web stream.
* **Smart Cropping:** Real-time "Crop Box" to save only the subject.

---

## 🔌 Quick Wiring Guide

* **Turntable Motor:** ESP32 Pins 8, 9, 10, 11
* **Elevator Motor:** ESP32 Pins 6, 5, 7, 4
* **Servo Motor:** Pin 3 (Signal)
* **Power:** Use external 5V 3A (Common Ground with ESP32).

---

## 🚀 How to Run

1. **ESP32:** Upload `v_2_2.ino` via Arduino IDE (Set your Wi-Fi).
2. **PC:** Install dependencies: `pip install flask flask-socketio requests pillow`
3. **Settings:** Update `ayarlar.json` with your ESP32's IP.
4. **Start:** Run `baslat.bat` and open `http://localhost:5000/monitor` on your PC.

---

## 📜 License
This project is licensed under **CC BY-NC** (Attribution-NonCommercial).

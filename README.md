# IoT Home Dashboard — Security Monitoring & Attack Simulation

A capstone IoT project demonstrating a real-time smart home monitoring system with a full IoT security attack and mitigation simulation.

Built with **ESP32**, **Raspberry Pi Pico 2W**, **STM32 ARM Blue Pill**, **Node-RED**, and **Mosquitto MQTT** — with a live attack demo using **Kali Linux**.

---

## 📸 System Overview

```
[STM32 Blue Pill]
      │  UART (PA9/PA10)
      ▼
[Pico 2W] ──── WiFi/MQTT ────┐
[ESP32]   ──── WiFi/MQTT ────┤──► [Mosquitto Broker (Docker)] ──► [Node-RED Dashboard]
                             │         Port 1883
[Kali Linux] ── Attack ──────┘    (secured / unsecured)
```

---

## 🔧 Hardware Used

| Device | Role |
|---|---|
| ESP32 | Temperature, Humidity (DHT11), Gas (MQ-2), Water Sensor, Buzzer, LED |
| Raspberry Pi Pico 2W | HC-SR04 Water Level, LED, UART bridge for STM32 |
| STM32 Blue Pill (F103C8) | ARM Cortex-M3 demo — Panic Button, LED, Internal Temp, Heartbeat |
| ST-Link V2 | STM32 programmer (SWD method) |
| Kali Linux Laptop | Attacker machine for security demo |
| Windows PC | Main server — Node-RED (local) + Mosquitto (Docker) |

---

## 💻 Software Stack

| Software | Purpose |
|---|---|
| Mosquitto (Docker) | MQTT Broker on port 1883 |
| Node-RED (local via Node.js) | Dashboard and flow logic |
| Arduino IDE | ESP32 and STM32 programming |
| Thonny IDE | Pico 2W MicroPython programming |
| STM32CubeProgrammer | STM32 upload via SWD |
| Python 3 + paho-mqtt | Attack and mitigation scripts |

---

## 📁 Repository Structure

```
├── README.md
├── INSTALLATION_GUIDE.txt       Full setup guide from scratch
├── demo_script.txt              Faculty presentation step-by-step guide
├── .gitignore
│
├── hardware code/
│   ├── esp32_main.ino           ESP32 Arduino code
│   ├── pico2w_main.py           Pico 2W MicroPython code (+ STM32 UART bridge)
│   ├── stm32_arm_node.ino       STM32 Blue Pill Arduino code
│   └── wiring guide             Pin connections for all devices
│
├── node red/
│   └── flow.json                Node-RED dashboard flow (import this)
│
├── mqtt/
│   ├── mosquitto_secure.conf    Broker config — authentication ON (normal use)
│   ├── mosquitto_unsecure.conf  Broker config — authentication OFF (attack demo)
│   └── acl                      ACL file for topic-level access control
│
└── attack/
    ├── spoof_attack.py          MQTT spoofing attack script (run on Kali)
    ├── mitigation_test.py       Tests that secured broker blocks the attack
    ├── security_demo.py         Combined demo reference script
    └── requirements.txt         Python dependencies
```

---

## 🚀 Quick Start

**Full step-by-step setup is in [`INSTALLATION_GUIDE.txt`](./INSTALLATION_GUIDE.txt)**

Short version:

1. **Clone the repo**
   ```bash
   git clone https://github.com/Dushyant68/IoT-Home-Dashboard-Security-Monitoring-and-Attack-Simulation-Public.git
   ```

2. **Start Mosquitto broker (Docker)**
   ```bash
   docker run -d --name mosquitto-broker -p 1883:1883 \
     -v ./mqtt:/mosquitto/config \
     eclipse-mosquitto
   ```

3. **Start Node-RED**
   ```bash
   node-red
   ```
   Then open `http://localhost:1880` and import `node red/flow.json`

4. **Flash hardware**
   - ESP32 → upload `esp32_main.ino` via Arduino IDE
   - Pico 2W → save `pico2w_main.py` as `main.py` via Thonny
   - STM32 → upload `stm32_arm_node.ino` via Arduino IDE (BOOT0=1, ST-Link SWD)

5. **Update WiFi and MQTT IP** in each device's code to match your network

---

## 🔒 Security Demo Summary

The project demonstrates a full IoT security attack lifecycle:

| Phase | Description |
|---|---|
| 1 — Normal Operation | System runs with authentication enabled. All sensors live, controls working. |
| 2 — Attack Setup | Broker switched to unsecured config (allow_anonymous true). Simulates real-world misconfiguration. |
| 3 — MQTT Spoofing | Kali runs `spoof_attack.py` — injects fake sensor data, triggers false alarms, controls physical devices remotely. |
| 4 — Eavesdropping | Kali subscribes to all topics without credentials — reads all sensor data. |
| 5 — Mitigation | Broker switched back to secured config. Attack scripts return Connection Refused. |

---

## 📡 MQTT Topics

| Topic | Device | Description |
|---|---|---|
| `esp32/temp` | ESP32 | Temperature (°C) |
| `esp32/hum` | ESP32 | Humidity (%) |
| `esp32/gas` | ESP32 | MQ-2 raw ADC value |
| `esp32/gas/status` | ESP32 | NORMAL or ALERT |
| `esp32/led` | Dashboard → ESP32 | LED control (ON/OFF) |
| `pico2/water/level` | Pico 2W | Water level (%) |
| `pico2/water/status` | Pico 2W | Status string |
| `pico2/led` | Dashboard → Pico 2W | LED control (ON/OFF) |
| `arm/temperature` | STM32 via Pico 2W | ARM internal temp |
| `arm/status` | STM32 via Pico 2W | ONLINE / OFFLINE |
| `arm/panic` | STM32 via Pico 2W | Panic button event |
| `arm/led` | Dashboard → STM32 | LED via Pico 2W bridge |

---

## ⚙️ STM32 Bridge Architecture

STM32 has no WiFi. It is wired to Pico 2W via UART:

```
STM32 PA9 (TX)  →  Pico 2W GP1 (RX)
STM32 PA10 (RX) →  Pico 2W GP0 (TX)
STM32 GND       →  Pico 2W GND
```

Pico 2W reads serial data from STM32 and publishes it to MQTT over WiFi. No bridge script on PC is needed.

---

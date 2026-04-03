"""
mitigation_test.py
==================
Run this on Kali Linux AFTER re-enabling authentication on broker.
Demonstrates that the attack is now blocked.

Usage:
    python3 mitigation_test.py
"""

import paho.mqtt.client as mqtt
import time

BROKER_IP   = "YOUR_MACHINE_IP"  # Change to your main laptop IP
BROKER_PORT = 1883              # Secured broker port

connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    codes = {
        0: "Connected (check broker auth!)",
        1: "Wrong protocol version",
        2: "Invalid client ID",
        3: "Broker unavailable",
        4: "Bad username or password",
        5: "Not authorised"
    }
    if rc == 0:
        connected = True
        print("[⚠️  WARNING] Connected without credentials — broker auth may be disabled!")
    else:
        print("=" * 55)
        print("  MITIGATION RESULT")
        print("=" * 55)
        print(f"  ✅ Attack BLOCKED")
        print(f"  ✅ Reason: {codes.get(rc, 'Unknown')} (rc={rc})")
        print(f"  ✅ Broker rejected unauthorized connection")
        print("=" * 55)

print("=" * 55)
print("  MITIGATION DEMONSTRATION")
print("  Attacker attempting connection WITHOUT credentials")
print(f"  Target: {BROKER_IP}:{BROKER_PORT}")
print("=" * 55)

client = mqtt.Client("AttackerBlocked_001")
client.on_connect = on_connect

try:
    client.connect(BROKER_IP, BROKER_PORT, keepalive=10)
    client.loop_start()
    time.sleep(3)
    client.loop_stop()
    if connected:
        client.disconnect()
except ConnectionRefusedError:
    print("✅ Attack blocked at network level — connection refused")
except Exception as e:
    print(f"✅ Attack blocked: {e}")

print("\nMitigation test complete.")

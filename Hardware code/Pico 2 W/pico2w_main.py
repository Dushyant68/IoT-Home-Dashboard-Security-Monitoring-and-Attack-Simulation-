# ─── Pico2W — Water Tank Monitor + STM32 Bridge ──────────────
# Sensors: HC-SR04 Ultrasonic
# Bridge: Reads STM32 Blue Pill via UART (GP0/GP1)
# Publishes: pico2/water/level, pico2/water/status
#            arm/temperature, arm/humidity, arm/status, arm/alert
# Subscribes: capstone/pico2/led, arm/led

import network
import time
from machine import Pin, UART, time_pulse_us
from umqtt.simple import MQTTClient
import ubinascii
import machine

# ─── Config ───────────────────────────────────────────────────
WIFI_SSID     = "D"
WIFI_PASSWORD = "987654321"
MQTT_BROKER   = "10.99.206.76"
MQTT_PORT     = 1883
MQTT_USER     = "testuser"
MQTT_PASSWORD = "testpass"
MQTT_CLIENT_ID = ubinascii.hexlify(machine.unique_id())

# ─── Pins ─────────────────────────────────────────────────────
TRIG_PIN    = Pin(14, Pin.OUT)
ECHO_PIN    = Pin(15, Pin.IN)
ONBOARD_LED = Pin("LED", Pin.OUT)

# ─── UART for STM32 ───────────────────────────────────────────
# GP0 = TX (Pico2W) → PA10 (STM32 RX)
# GP1 = RX (Pico2W) → PA9  (STM32 TX)
stm32_uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

# ─── Tank Config ──────────────────────────────────────────────
TANK_MAX_CM = 30
TANK_MIN_CM = 3

# ─── Topics ───────────────────────────────────────────────────
TOPIC_WATER_LEVEL  = b"pico2/water/level"
TOPIC_WATER_STATUS = b"pico2/water/status"
TOPIC_PICO_LED     = b"capstone/pico2/led"
TOPIC_ARM_TEMP     = b"arm/temperature"
TOPIC_ARM_STATUS   = b"arm/status"
TOPIC_ARM_ALERT    = b"arm/alert"
TOPIC_ARM_LED      = b"arm/led"

# ─────────────────────────────────────────────────────────────
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi:", WIFI_SSID)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 0
        while not wlan.isconnected():
            time.sleep(0.5)
            print(".", end="")
            timeout += 1
            if timeout > 30:
                print("\nWiFi timeout! Rebooting...")
                machine.reset()
    print("\nWiFi connected! IP:", wlan.ifconfig()[0])
    return wlan

# ─────────────────────────────────────────────────────────────
def measure_distance():
    TRIG_PIN.value(0)
    time.sleep_us(2)
    TRIG_PIN.value(1)
    time.sleep_us(10)
    TRIG_PIN.value(0)
    duration = time_pulse_us(ECHO_PIN, 1, 30000)
    if duration < 0:
        return -1
    return round((duration / 2) / 29.1, 1)

def distance_to_level(distance_cm):
    if distance_cm < 0:
        return -1
    level = (TANK_MAX_CM - distance_cm) / (TANK_MAX_CM - TANK_MIN_CM) * 100
    return round(max(0, min(100, level)), 1)

def get_water_status(level):
    if level < 0:   return "ERROR"
    elif level < 20: return "CRITICAL"
    elif level < 40: return "LOW"
    else:            return "OK"

# ─────────────────────────────────────────────────────────────
def mqtt_callback(topic, msg):
    topic = topic.decode()
    msg   = msg.decode().strip()
    print("MQTT [{}]: {}".format(topic, msg))

    if topic == "capstone/pico2/led":
        ONBOARD_LED.value(1 if msg == "ON" else 0)

    elif topic == "arm/led":
        # Forward to STM32 via UART
        cmd = "LED:ON\n" if msg == "ON" else "LED:OFF\n"
        stm32_uart.write(cmd.encode())
        print("Sent to STM32:", cmd.strip())

# ─────────────────────────────────────────────────────────────
def connect_mqtt():
    client = MQTTClient(
        MQTT_CLIENT_ID, MQTT_BROKER,
        port=MQTT_PORT, user=MQTT_USER,
        password=MQTT_PASSWORD, keepalive=10
    )
    client.set_callback(mqtt_callback)
    # Last will — published automatically if connection drops
    client.set_last_will(
        b"arm/status",
        b"OFFLINE",
        retain=True,
        qos=0
    )
    client.connect()
    client.subscribe(TOPIC_PICO_LED)
    client.subscribe(TOPIC_ARM_LED)
    print("MQTT Connected!")
    return client

# ─────────────────────────────────────────────────────────────
stm32_buffer = ""

def read_stm32(client):
    global stm32_buffer
    while stm32_uart.any():
        try:
            char = stm32_uart.read(1).decode("utf-8")
            if char == '\n':
                line = stm32_buffer.strip()
                stm32_buffer = ""
                if line:
                    print("STM32:", line)
                    if line.startswith("TEMP:") and line != "TEMP:ERROR":
                        val = line.split(":")[1]
                        client.publish(TOPIC_ARM_TEMP, val.encode())
                    elif line.startswith("STATUS:"):
                        val = line.split(":")[1]
                        client.publish(TOPIC_ARM_STATUS, val.encode())
                    elif line.startswith("ALERT:"):
                        val = line.split(":")[1]
                        client.publish(TOPIC_ARM_ALERT, val.encode())
                        client.publish(b"capstone/panic/email", val.encode())
                        print("ARM ALERT:", val)
            else:
                stm32_buffer += char
        except Exception as e:
            print("UART error:", e)
            stm32_buffer = ""
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 40)
    print("  Pico2W — Water + STM32 Bridge")
    print("=" * 40)

    connect_wifi()

    client = None
    while client is None:
        try:
            client = connect_mqtt()
        except Exception as e:
            print("MQTT failed:", e, "retrying...")
            time.sleep(5)

    # Ready blink
    for _ in range(3):
        ONBOARD_LED.value(1)
        time.sleep(0.2)
        ONBOARD_LED.value(0)
        time.sleep(0.2)

    print("System ready!")
    last_publish = 0

    while True:
        try:
            client.check_msg()
            read_stm32(client)

            now = time.ticks_ms()
            if time.ticks_diff(now, last_publish) >= 3000:
                last_publish = now

                # Water level
                distance = measure_distance()
                level    = distance_to_level(distance)
                status   = get_water_status(level)

                print("Distance:{}cm Level:{}% Status:{}".format(
                    distance, level, status))

                if level >= 0:
                    client.publish(TOPIC_WATER_LEVEL,  str(level).encode())
                    client.publish(TOPIC_WATER_STATUS, status.encode())
                else:
                    client.publish(TOPIC_WATER_STATUS, b"ERROR")

        except Exception as e:
            print("Error:", e, "— reconnecting...")
            time.sleep(3)
            try:
                client = connect_mqtt()
            except:
                time.sleep(5)

main()


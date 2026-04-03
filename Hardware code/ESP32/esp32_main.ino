#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ─── Config ───────────────────────────────────────────────────
const char* ssid        = "YOUR_HOTSPOT_NAME";
const char* password    = "YOUR_HOTSPOT_PASSWORD";
const char* mqtt_server = "YOUR_MACHINE_IP";
const int   mqtt_port   = 1883;
const char* mqtt_user   = "testuser";
const char* mqtt_pass   = "YOUR_MQTT_PASSWORD";

// ─── Pins ─────────────────────────────────────────────────────
#define DHTPIN        4
#define DHTTYPE       DHT11
#define MQ2_PIN       34
#define BUZZER_PIN    26
#define ONBOARD_LED   2
#define SDA_PIN       21
#define SCL_PIN       22

// ─── Topics ───────────────────────────────────────────────────
#define TOPIC_TEMP        "esp32/temp"
#define TOPIC_HUM         "esp32/hum"
#define TOPIC_GAS         "esp32/gas"
#define TOPIC_GAS_STATUS  "esp32/gas/status"
#define TOPIC_ALERT       "capstone/alert"
#define TOPIC_LED         "capstone/esp32/led"
#define TOPIC_BUZZER      "capstone/esp32/buzzer"

// ─── Thresholds ───────────────────────────────────────────────
#define GAS_THRESHOLD   2500
#define TEMP_THRESHOLD  35.0

// ─── Objects ──────────────────────────────────────────────────
DHT dht(DHTPIN, DHTTYPE);
WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// ─── Timing ───────────────────────────────────────────────────
unsigned long lastSensorRead = 0;
unsigned long lastLCDSwitch  = 0;
const long sensorInterval    = 3000;
const long lcdSwitchInterval = 4000;

// ─── State ────────────────────────────────────────────────────
int   lcdScreen    = 0;
bool  buzzerActive = false;
bool  manualBuzzer = false;  // FIX: tracks if buzzer was manually turned on
float currentTemp  = 0;
float currentHum   = 0;
int   currentGas   = 0;
bool  gasAlert     = false;

// ─────────────────────────────────────────────────────────────
void setup_wifi() {
  Serial.print("Connecting WiFi...");
  lcd.clear(); lcd.setCursor(0,0); lcd.print("Connecting WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.println("\nWiFi OK! IP: " + WiFi.localIP().toString());
  lcd.clear(); lcd.setCursor(0,0); lcd.print("WiFi Connected!");
  lcd.setCursor(0,1); lcd.print(WiFi.localIP());
  delay(2000);
}

// ─────────────────────────────────────────────────────────────
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.println("MQTT [" + String(topic) + "]: " + msg);

  if (String(topic) == TOPIC_LED)
    digitalWrite(ONBOARD_LED, msg == "ON" ? HIGH : LOW);

  if (String(topic) == TOPIC_BUZZER) {
    if (msg == "ON") {
      digitalWrite(BUZZER_PIN, HIGH);
      buzzerActive  = true;
      manualBuzzer  = true;   // Mark as manually controlled
    } else {
      digitalWrite(BUZZER_PIN, LOW);
      buzzerActive  = false;
      manualBuzzer  = false;  // Released manual control
    }
  }
}

// ─────────────────────────────────────────────────────────────
void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting MQTT...");
    lcd.clear(); lcd.setCursor(0,0); lcd.print("MQTT connecting");
    String clientId = "ESP32-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("Connected!");
      client.subscribe(TOPIC_LED);
      client.subscribe(TOPIC_BUZZER);
      lcd.clear(); lcd.setCursor(0,0); lcd.print("MQTT Connected!");
      delay(1500);
    } else {
      Serial.println("Failed rc=" + String(client.state()));
      lcd.setCursor(0,1); lcd.print("Retry in 5s...");
      delay(5000);
    }
  }
}

// ─────────────────────────────────────────────────────────────
void read_and_publish_sensors() {
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();

  if (!isnan(temp) && !isnan(hum)) {
    currentTemp = temp; currentHum = hum;
    client.publish(TOPIC_TEMP, String(temp, 1).c_str());
    client.publish(TOPIC_HUM,  String(hum,  1).c_str());
    Serial.println("T:" + String(temp) + " H:" + String(hum));
    if (temp > TEMP_THRESHOLD) client.publish(TOPIC_ALERT, "HIGH_TEMP");
  } else {
    Serial.println("DHT11 read failed!");
  }

  int gasValue = analogRead(MQ2_PIN);
  currentGas = gasValue;
  client.publish(TOPIC_GAS, String(gasValue).c_str());

  if (gasValue > GAS_THRESHOLD) {
    gasAlert = true;
    client.publish(TOPIC_GAS_STATUS, "ALERT");
    client.publish(TOPIC_ALERT, "GAS_DETECTED");
    // Only auto-trigger buzzer if not manually controlled
    if (!manualBuzzer && !buzzerActive) {
      digitalWrite(BUZZER_PIN, HIGH);
      buzzerActive = true;
    }
  } else {
    gasAlert = false;
    client.publish(TOPIC_GAS_STATUS, "NORMAL");
    // Only auto-turn off if not manually controlled
    if (!manualBuzzer && buzzerActive) {
      digitalWrite(BUZZER_PIN, LOW);
      buzzerActive = false;
    }
  }
}

// ─────────────────────────────────────────────────────────────
void update_lcd() {
  if (millis() - lastLCDSwitch < lcdSwitchInterval) return;
  lastLCDSwitch = millis();
  lcd.clear();

  switch (lcdScreen) {
    case 0:
      lcd.setCursor(0,0); lcd.print("Temp:"); lcd.print(currentTemp,1); lcd.print((char)223); lcd.print("C");
      lcd.setCursor(0,1); lcd.print("Humi:"); lcd.print(currentHum,1);  lcd.print("%");
      break;
    case 1:
      lcd.setCursor(0,0); lcd.print("Gas:"); lcd.print(currentGas);
      lcd.setCursor(0,1); lcd.print(gasAlert ? "!! GAS ALERT !!" : "Status:NORMAL");
      break;
    case 2:
      lcd.setCursor(0,0); lcd.print(WiFi.localIP());
      lcd.setCursor(0,1); lcd.print(client.connected() ? "MQTT: OK" : "MQTT: ERR");
      break;
  }
  lcdScreen = (lcdScreen + 1) % 3;
}

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  pinMode(ONBOARD_LED, OUTPUT);
  pinMode(BUZZER_PIN,  OUTPUT);
  digitalWrite(ONBOARD_LED, LOW);
  digitalWrite(BUZZER_PIN,  LOW);

  Wire.begin(SDA_PIN, SCL_PIN);
  lcd.init(); lcd.backlight();
  lcd.setCursor(0,0); lcd.print("ESP32 IoT Node");
  lcd.setCursor(0,1); lcd.print("Starting...");
  delay(2000);

  dht.begin();
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(mqtt_callback);
  Serial.println("ESP32 Ready!");
}

// ─────────────────────────────────────────────────────────────
void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  if (millis() - lastSensorRead >= sensorInterval) {
    lastSensorRead = millis();
    read_and_publish_sensors();
  }
  update_lcd();
}

// ─── STM32 Blue Pill — ARM IoT Node ──────────────────────────
// Components: Button (PB0), External LED (PB1), Onboard LED (PC13)
// Temperature: STM32 built-in internal sensor
// Communication: UART Serial1 → Pico2W → MQTT
// Baud: 9600

#define BUTTON_PIN   PB0
#define EXT_LED_PIN  PB1
#define ONBOARD_LED  PC13   // Active LOW on Blue Pill

unsigned long lastPublish = 0;
bool lastButtonState      = HIGH;
bool extLedState          = false;

// ─────────────────────────────────────────────────────────────
float read_internal_temp() {
  analogReadResolution(12);
  int raw       = analogRead(ATEMP);
  float voltage = raw * (3.3f / 4095.0f);
  float temp    = ((1.43f - voltage) / 0.00430f) + 25.0f;
  return temp;
}

// ─────────────────────────────────────────────────────────────
void setup() {
  Serial1.begin(9600);  // PA9=TX → Pico2W GP1 | PA10=RX ← Pico2W GP0

  pinMode(BUTTON_PIN,  INPUT_PULLUP);
  pinMode(EXT_LED_PIN, OUTPUT);
  pinMode(ONBOARD_LED, OUTPUT);

  digitalWrite(EXT_LED_PIN, LOW);
  digitalWrite(ONBOARD_LED, HIGH);  // HIGH = OFF (active low)

  delay(2000);

  // Blink 3 times on startup then stay OFF
  for (int i = 0; i < 3; i++) {
    digitalWrite(ONBOARD_LED, LOW);   // ON
    delay(200);
    digitalWrite(ONBOARD_LED, HIGH);  // OFF
    delay(200);
  }
  // LED stays OFF after startup — clean look
  digitalWrite(ONBOARD_LED, HIGH);

  Serial1.println("STATUS:ONLINE");
  Serial1.println("INFO:STM32 ARM Node Ready");
}

// ─────────────────────────────────────────────────────────────
void check_button() {
  bool current = digitalRead(BUTTON_PIN);
  if (current == LOW && lastButtonState == HIGH) {
    delay(50);
    if (digitalRead(BUTTON_PIN) == LOW) {
      Serial1.println("ALERT:PANIC_BUTTON_PRESSED");
      // Flash 3 times as button press feedback
      for (int i = 0; i < 3; i++) {
        digitalWrite(ONBOARD_LED, LOW);
        delay(100);
        digitalWrite(ONBOARD_LED, HIGH);
        delay(100);
      }
      // Stay OFF after flash
      digitalWrite(ONBOARD_LED, HIGH);
    }
  }
  lastButtonState = current;
}

// ─────────────────────────────────────────────────────────────
void check_commands() {
  if (Serial1.available()) {
    String cmd = Serial1.readStringUntil('\n');
    cmd.trim();
    if (cmd == "LED:ON") {
      digitalWrite(EXT_LED_PIN, HIGH);
      extLedState = true;
      Serial1.println("ACK:LED_ON");
    } else if (cmd == "LED:OFF") {
      digitalWrite(EXT_LED_PIN, LOW);
      extLedState = false;
      Serial1.println("ACK:LED_OFF");
    }
  }
}

// ─────────────────────────────────────────────────────────────
void publish_sensors() {
  unsigned long now = millis();
  if (now - lastPublish >= 3000) {
    lastPublish = now;
    float temp  = read_internal_temp();
    if (temp > -40 && temp < 125) {
      Serial1.print("TEMP:"); Serial1.println(temp, 1);
    } else {
      Serial1.println("TEMP:ERROR");
    }
    Serial1.println("STATUS:ONLINE");
  }
}

// ─────────────────────────────────────────────────────────────
void loop() {
  check_button();
  check_commands();
  publish_sensors();
}

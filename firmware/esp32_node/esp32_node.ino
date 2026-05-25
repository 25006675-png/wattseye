/*
 * WattsEye ESP32 node — occupancy sensing + AC cutoff actuator
 * =============================================================
 * One ESP32 does three jobs (see HARDWARE_CONNECTION.md §10, §11, §13):
 *   1. Read the LD2410C mmWave presence pin and publish occupancy over MQTT.
 *   2. Subscribe to AC cutoff commands from the Pi bridge.
 *   3. On "off", transmit the AC's IR "off" frame AND open the demo relay.
 *
 * MQTT contract (matches backend/pi_bridge.py):
 *   PUBLISH  wattseye/occupancy : {"occupied":bool,"room":"living","ts":millis}
 *   PUBLISH  wattseye/ac/state  : {"relay":"on"|"off","ir_sent":bool,"ts":millis}
 *   SUBSCRIBE wattseye/ac/command: {"command":"off"|"on","reason":"...","ts":...}
 *
 * Libraries (install via Arduino IDE Library Manager / PlatformIO):
 *   - PubSubClient            (knolleary)      MQTT client
 *   - ArduinoJson             (bblanchon)      JSON encode/decode
 *   - IRremoteESP8266         (crankyoldgit)   IR transmit (works on ESP32 too)
 * Board: any ESP32 dev board (e.g. ESP32-WROOM DevKitC).
 *
 * Wiring (HARDWARE_CONNECTION.md):
 *   LD2410C OUT/OT2 -> GPIO5   (digital presence: HIGH=occupied)   §10.2
 *   IR LED (via 2N2222 base 1k, LED series 100R) -> GPIO4          §11.1
 *   Relay IN        -> GPIO18  (active-LOW module: LOW=energise)   §13.3
 *
 * SET THESE before flashing:  WIFI_SSID, WIFI_PASS, MQTT_HOST.
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include <IRremoteESP8266.h>
#include <IRsend.h>
// For a real inverter AC, also include its protocol, e.g.:
// #include <ir_Daikin.h>

// ---------------- USER CONFIG ----------------
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* MQTT_HOST = "192.168.0.50";   // Raspberry Pi IP running Mosquitto
const int   MQTT_PORT = 1883;
const char* ROOM_NAME = "living";

// Set true to send a real AC brand frame instead of the demo NEC pulse.
#define USE_REAL_AC false

// ---------------- PINS ----------------
const int PRESENCE_PIN = 5;    // LD2410C OUT/OT2
const int IR_LED_PIN   = 4;    // IR LED driver (2N2222 base)
const int RELAY_PIN    = 18;   // relay IN (active-LOW)

// ---------------- TOPICS ----------------
const char* TOPIC_OCC = "wattseye/occupancy";
const char* TOPIC_CMD = "wattseye/ac/command";
const char* TOPIC_STATE = "wattseye/ac/state";

// ---------------- GLOBALS ----------------
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
IRsend irsend(IR_LED_PIN);
// #if USE_REAL_AC
// IRDaikinESP ac(IR_LED_PIN);
// #endif

bool lastOccupied = true;          // force a publish on first read
unsigned long lastOccPublish = 0;
const unsigned long OCC_PUBLISH_MS = 1000;   // heartbeat occupancy at 1 Hz

// Relay helpers (active-LOW: LOW closes NO -> socket powered).
void acSimOn()  { digitalWrite(RELAY_PIN, LOW);  }
void acSimOff() { digitalWrite(RELAY_PIN, HIGH); }

void sendIrOff() {
#if USE_REAL_AC
  // ac.off(); ac.send();   // uncomment with the right brand object included
#else
  irsend.sendNEC(0x00FF02FD, 32);   // any 38 kHz frame triggers the demo VS1838B
#endif
}

void publishAcState(bool relayOn, bool irSent) {
  StaticJsonDocument<128> doc;
  doc["relay"] = relayOn ? "on" : "off";
  doc["ir_sent"] = irSent;
  doc["ts"] = millis();
  char buf[128];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(TOPIC_STATE, buf, n);
}

void handleCommand(const char* payload) {
  StaticJsonDocument<192> doc;
  if (deserializeJson(doc, payload)) return;          // ignore malformed JSON
  const char* command = doc["command"] | "";
  if (strcmp(command, "off") == 0) {
    sendIrOff();
    acSimOff();
    publishAcState(false, true);
    Serial.println("AC cutoff: IR sent + relay opened");
  } else if (strcmp(command, "on") == 0) {
    acSimOn();
    publishAcState(true, false);
    Serial.println("AC restored: relay closed");
  }
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  char buf[256];
  unsigned int n = length < sizeof(buf) - 1 ? length : sizeof(buf) - 1;
  memcpy(buf, payload, n);
  buf[n] = '\0';
  if (strcmp(topic, TOPIC_CMD) == 0) handleCommand(buf);
}

void publishOccupancy(bool occupied) {
  StaticJsonDocument<128> doc;
  doc["occupied"] = occupied;
  doc["room"] = ROOM_NAME;
  doc["ts"] = millis();
  char buf[128];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(TOPIC_OCC, buf, n);
  Serial.printf("occupancy -> %s\n", occupied ? "OCCUPIED" : "EMPTY");
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi connecting");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.printf("\nWiFi up: %s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMqttMessage);
  while (!mqtt.connected()) {
    Serial.print("MQTT connecting...");
    if (mqtt.connect("wattseye-esp32")) {
      mqtt.subscribe(TOPIC_CMD);
      Serial.println("connected, subscribed ac/command");
    } else {
      Serial.printf("failed rc=%d, retry in 2s\n", mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PRESENCE_PIN, INPUT);
  pinMode(RELAY_PIN, OUTPUT);
  acSimOn();                 // default: AC-SIM socket powered at boot
  irsend.begin();
  connectWifi();
  connectMqtt();
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  bool occupied = digitalRead(PRESENCE_PIN) == HIGH;
  unsigned long now = millis();
  // Publish on change immediately, and as a 1 Hz heartbeat otherwise.
  if (occupied != lastOccupied || (now - lastOccPublish) >= OCC_PUBLISH_MS) {
    publishOccupancy(occupied);
    lastOccupied = occupied;
    lastOccPublish = now;
  }
  delay(50);
}

/*
 * WattsEye ESP32 AC cutoff node
 * ------------------------------------------------------------------
 * Subscribes to the Pi's MQTT broker and drives a relay (fan demo / AC).
 *
 *   SUBSCRIBES  wattseye/ac/command   {"command":"off"|"on","reason":"...","ts":"..."}
 *   PUBLISHES   wattseye/ac/state     {"relay":"on"|"off","ir_sent":bool,"ts_ms":...}
 *
 * The Pi's smart rule publishes {"command":"off"} when a room is empty
 * and the AC/fan is on past the threshold. This node opens the relay to cut
 * the fan. For a real AC, also send an IR "off" frame in sendIrOff().
 *
 * Libraries:
 *   - PubSubClient
 *   - ArduinoJson v6+
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ===================== CONFIG: EDIT BEFORE UPLOAD =====================
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

const char* MQTT_HOST = "10.48.196.135";
const uint16_t MQTT_PORT = 1883;

const int RELAY_PIN = 26;
const bool RELAY_ACTIVE_HIGH = false;  // many relay modules are active-LOW
const bool START_FAN_ON = true;
// =====================================================================

const char* TOPIC_COMMAND = "wattseye/ac/command";
const char* TOPIC_STATE = "wattseye/ac/state";
const char* CLIENT_ID = "wattseye-esp32-ac";

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
bool fanOn = false;

void setRelay(bool on) {
  fanOn = on;
  bool level = RELAY_ACTIVE_HIGH ? on : !on;
  digitalWrite(RELAY_PIN, level ? HIGH : LOW);
  Serial.printf("[relay] fan %s\n", on ? "ON" : "OFF (cut)");
}

bool sendIrOff() {
  return false;
}

void publishState(bool irSent) {
  StaticJsonDocument<128> doc;
  doc["relay"] = fanOn ? "on" : "off";
  doc["ir_sent"] = irSent;
  doc["ts_ms"] = millis();

  char buf[128];
  size_t n = serializeJson(doc, buf);
  mqtt.publish(TOPIC_STATE, buf, n);
}

void onMessage(char* topic, byte* payload, unsigned int len) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, len)) {
    Serial.println("[mqtt] bad JSON payload");
    return;
  }

  const char* command = doc["command"] | "";
  Serial.printf(
    "[mqtt] command=%s reason=%s\n",
    command,
    (const char*)(doc["reason"] | "")
  );

  if (strcmp(command, "off") == 0) {
    bool irSent = sendIrOff();
    setRelay(false);
    publishState(irSent);
  } else if (strcmp(command, "on") == 0) {
    setRelay(true);
    publishState(false);
  }
}

void connectWifi() {
  Serial.printf("[wifi] connecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.printf("\n[wifi] connected, ip=%s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.printf("[mqtt] connecting to %s:%u ... ", MQTT_HOST, MQTT_PORT);
    if (mqtt.connect(CLIENT_ID)) {
      Serial.println("ok");
      mqtt.subscribe(TOPIC_COMMAND, 1);
      publishState(false);
    } else {
      Serial.printf("failed rc=%d, retry in 2s\n", mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  pinMode(RELAY_PIN, OUTPUT);
  setRelay(START_FAN_ON);

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
  connectMqtt();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
}

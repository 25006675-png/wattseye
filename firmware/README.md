# WattsEye Firmware

Microcontroller code for the WattsEye demo rig. These are **workstream #4**
("ESP32 control system") from [`plan/07_TASK_BREAKDOWN.md`](../plan/07_TASK_BREAKDOWN.md).
Wiring and pin choices are defined in
[`../HARDWARE_CONNECTION.md`](../HARDWARE_CONNECTION.md) §10–§13.

| Sketch | Board | Role |
|---|---|---|
| `esp32_node/esp32_node.ino` | ESP32 dev board | Live: occupancy → MQTT, AC cutoff (IR + relay) ← MQTT |
| `arduino_ir_learn/arduino_ir_learn.ino` | Arduino Nano/Uno (or ESP32) | One-time: capture your real AC remote's IR codes |

## 1. Toolchain

Either **Arduino IDE 2.x** or **PlatformIO**. Add the ESP32 board support
(Boards Manager → "esp32" by Espressif).

## 2. Libraries (Library Manager)

For `esp32_node`:
- **PubSubClient** (knolleary) — MQTT
- **ArduinoJson** (bblanchon)
- **IRremoteESP8266** (crankyoldgit) — IR transmit (also works on ESP32)

For `arduino_ir_learn`:
- **IRremote** (z3t0 / Armin Joachimsmeyer), v3.x+

> Note the two sketches use *different* IR libraries on purpose: `IRremoteESP8266`
> is the de-facto choice for ESP-family transmit with per-brand AC objects;
> `IRremote` is the classic AVR library with the nicest capture/printout for the
> learn step. Don't install both into the same sketch.

## 3. Configure before flashing

In `esp32_node.ino`, edit the **USER CONFIG** block:
```cpp
const char* WIFI_SSID = "...";
const char* WIFI_PASS = "...";
const char* MQTT_HOST = "192.168.0.50";   // the Pi's LAN IP (Mosquitto)
#define USE_REAL_AC false                  // true once you've learned a brand frame
```
Find the Pi's IP with `hostname -I` on the Pi.

## 4. MQTT contract (must match `backend/pi_bridge.py`)

| Direction | Topic | Payload |
|---|---|---|
| ESP32 → Pi | `wattseye/occupancy` | `{"occupied":true,"room":"living","ts":123}` |
| ESP32 → Pi | `wattseye/ac/state` | `{"relay":"on","ir_sent":true,"ts":123}` |
| Pi → ESP32 | `wattseye/ac/command` | `{"command":"off","reason":"empty_room_waste","ts":...}` |

## 5. Bring-up order

1. Flash `arduino_ir_learn`, open Serial Monitor @115200, press your AC remote's
   OFF — note the protocol/value (or raw buffer). Skip if you only demo with the
   relay path (any 38 kHz pulse triggers the demo VS1838B).
2. Flash `esp32_node`. Watch Serial: it should join WiFi, connect to MQTT, and
   print `occupancy -> OCCUPIED/EMPTY` as you enter/leave the sensor's view.
3. From the Pi, publish a manual cutoff to confirm the actuator path:
   ```bash
   mosquitto_pub -t wattseye/ac/command -m '{"command":"off","reason":"test"}'
   ```
   The IR LED fires (check with a phone camera — §11.4) and the relay opens.
4. Run the full chain: `ads1115_reader` + `pi_bridge` on the Pi (see
   HARDWARE_CONNECTION.md §15) and let an empty room trigger the cutoff.

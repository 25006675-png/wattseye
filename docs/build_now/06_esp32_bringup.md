# Step 6 — ESP32 node: occupancy + IR + relay

**Goal:** flash the ESP32 so it (1) reads the LD2410C presence sensor and publishes
occupancy over MQTT, and (2) on an "off" command, fires the IR LED and opens the
demo relay. This is the **actuator side** of the rig.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md) §10
(occupancy), §11 (IR), §13 (relay). **Sketch:**
[`../../firmware/esp32_node/esp32_node.ino`](../../firmware/esp32_node/esp32_node.ino).

> 🟢 Safe bench task — 3.3 V/5 V logic only, USB powered. No mains. ⏱️ ~1–2 h.
> Needs the IR driver + relay from [Step 4](04_breadboard_circuits.md) and a broker
> (the **Pi** from [Step 3](03_pi_run.md), or your laptop from [Step 1](01_laptop_software_loop.md)).

---

## ⚠️ Step 6.0 — Identify your board FIRST

The BOM lists *"NodeMCU / ESP32 (ESP-12E / ESP8266)"* — two different chips. The
shipped sketch targets **ESP32**. Check the silk/can on your board:

| Board says… | It's a… | Core to install | `WiFi` include |
|---|---|---|---|
| **ESP32**, ESP32-WROOM, DevKitC, 38 pins | **ESP32** ✅ | "esp32 by Espressif" | `#include <WiFi.h>` (already) |
| **ESP-12E**, NodeMCU, ESP8266, 30 pins | **ESP8266** | "esp8266 by ESP8266 Community" | needs `#include <ESP8266WiFi.h>` |

If you have an **ESP8266**, see the [porting note](#appendix--if-you-have-an-esp8266)
at the bottom. The rest assumes ESP32.

---

## What you need

- Your **ESP32 dev board** + USB cable → laptop
- **LD2410C** presence sensor + jumper wires
- The **IR LED driver** and **relay** from [Step 4](04_breadboard_circuits.md)
- A broker running (Pi from Step 3, or laptop from Step 1)

---

## Step 6.1 — Install ESP32 board support

1. **File → Preferences →** "Additional boards manager URLs", paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
2. **Tools → Board → Boards Manager…**, search `esp32`, install
   **"esp32 by Espressif Systems"**.

> Clones use a **CP2102** or **CH340** USB chip — if no COM port appears, install
> that chip's Windows driver.

## Step 6.2 — Install the three libraries

**Tools → Manage Libraries…**:
- **PubSubClient** (Nick O'Leary) — MQTT
- **ArduinoJson** (Benoit Blanchon)
- **IRremoteESP8266** (crankyoldgit) — IR transmit (works on ESP32 too)

> This is `IRremoteESP8266`, **not** the plain `IRremote` from the optional IR-learn.

## Step 6.3 — Wire the sensor + actuators

| Module | Module pin | ESP32 GPIO |
|---|---|---|
| **LD2410C** | `OUT` / `OT2` | **GPIO5** (HIGH = occupied) |
| LD2410C | `VCC` / `GND` | **5V** / **GND** |
| **IR LED** (via 2N2222 driver, Step 4) | driver base side | **GPIO4** |
| **Relay** `IN` | | **GPIO18** (active-LOW) |
| Relay `VCC` / `GND` | | **5V** / **GND** |

> 💡 Bring these up **one at a time** — start with just the LD2410C (Step 6.4).

## Step 6.4 — (Optional) Quick LD2410C test, no WiFi/MQTT

New sketch (File → New), paste, select your ESP32 board + port, upload, Serial
Monitor @ 115200:

```cpp
const int PRESENCE_PIN = 5;   // LD2410C OUT/OT2 -> GPIO5
void setup() { Serial.begin(115200); pinMode(PRESENCE_PIN, INPUT); }
void loop()  {
  Serial.println(digitalRead(PRESENCE_PIN) == HIGH ? "OCCUPIED" : "EMPTY");
  delay(500);
}
```

Walk past → `OCCUPIED`; step away and stay still → `EMPTY`. If that works, the
sensor and wiring are good.

## Step 6.5 — Configure `esp32_node.ino`

Open [`firmware/esp32_node/esp32_node.ino`](../../firmware/esp32_node/esp32_node.ino),
edit the **USER CONFIG** block:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* MQTT_HOST = "192.168.0.50";   // <-- the Pi's IP (Step 2.5), or your laptop's
const int   MQTT_PORT = 1883;
const char* ROOM_NAME = "living";
#define USE_REAL_AC false   // leave false for the demo (mock 38 kHz pulse)
```

- **`MQTT_HOST`** = the **Pi's IP** (`hostname -I` from Step 2.5) if the Pi runs the
  broker (Step 3), or your **laptop's IP** (`ipconfig`) if using the Step 1 broker.
- ESP32 + broker host must be on the **same 2.4 GHz WiFi**.

## Step 6.6 — Flash and watch

1. **Tools → Board →** your ESP32 (e.g. "ESP32 Dev Module"); **Port →** its COM.
2. **Upload.** *(Some boards: hold **BOOT** while it says "Connecting…".)*
3. Serial Monitor @ **115200**:
   ```
   WiFi up: 192.168.1.45
   MQTT connecting...connected, subscribed ac/command
   occupancy -> OCCUPIED
   ```

## Step 6.7 — Test the full command loop

On the broker host (Pi or laptop):

```bash
mosquitto_sub -h localhost -t "wattseye/#" -v          # watch
mosquitto_pub  -h localhost -t wattseye/ac/command -m '{"command":"off"}'   # trigger
```

On `off` the ESP32 prints `AC cutoff: IR sent + relay opened`, the **relay clicks**,
and the **IR LED flashes** (verify with a phone camera — §11.4). Send
`{"command":"on"}` to restore. 🎉 The actuator path works.

## Step 6.8 — (Optional) real AC code

Once the optional [IR-learn](09_ir_learn.md) gives you the AC's OFF frame, plug it
into `sendIrOff()` (clean protocol → `irsend.sendXXX`; brand → brand object +
`USE_REAL_AC true`; `UNKNOWN` → `irsend.sendRaw(...)`). See §11.2.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| No COM port | Install **CP2102**/**CH340** driver; try another cable |
| Upload stuck at "Connecting…" | Hold **BOOT** during upload |
| `WiFi connecting....` forever | SSID/pass typo; ESP32 is **2.4 GHz only** |
| `MQTT connecting...failed rc=-2` | Wrong `MQTT_HOST`; broker not on `0.0.0.0` (Step 3.2); firewall on port 1883 |
| Occupancy stuck OCCUPIED | LD2410C is motion-sensitive; stand fully out of view; check GPIO5 |
| IR LED never flashes | 2N2222 orientation (E-B-C), LED polarity, 100 Ω in LED line — Step 4 |
| Relay never clicks | active-HIGH vs LOW: flip HLT jumper or invert in code; check GPIO18 |

---

## Appendix — if you have an ESP8266

1. **Boards URL:** `http://arduino.esp8266.com/stable/package_esp8266com_index.json`,
   install "esp8266 by ESP8266 Community"; select e.g. "NodeMCU 1.0".
2. Change `#include <WiFi.h>` → `#include <ESP8266WiFi.h>`.
3. GPIO mapping: `PRESENCE_PIN` → `D5` (GPIO14), `IR_LED_PIN` → `D2` (GPIO4),
   `RELAY_PIN` → `D1` (GPIO5).
4. The three libraries work unchanged.

If unsure which board you have, send a photo to the team before flashing.

---

← Prev: [Step 5 — Sensing chain](05_sensing_chain.md) ·
Next: [Step 7 — Mains box](07_mains_box.md) →

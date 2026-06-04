# Deploying WattsEye to the Raspberry Pi

This is the checklist for taking the repo from a dev laptop to a live Pi with real
hardware. The code and MQTT contracts are deployment-ready; the work here is
config that deliberately doesn't live in git (secrets, hardware calibration,
WiFi), plus flashing the ESP32.

## What runs where

```
  ┌── Raspberry Pi ─────────────────────────────────────────────┐
  │  mosquitto            (MQTT broker, :1883)                   │
  │  ads1115_reader  ──wattseye/power──►  pi_bridge ──► live_state.json
  │                                          │  ▲              │      │
  │  api_server  ◄── live_state.json ────────┘  │              │      │
  │     │  └── reminders daemon ──► WhatsApp     │              ▼      │
  └─────┼───────────────────────────────────────┼── HTTP :8080 ┘      │
        │                                        │
   Flutter app (phone/PC)              ESP32 node (WiFi)
        WATTSEYE_API_BASE          occupancy ─►  / ◄─ ac/command (IR+relay)
```

Four Pi processes (`mosquitto`, `ads1115_reader`, `pi_bridge`, `api_server`) plus
the flashed ESP32 and the app. The **remind→WhatsApp** path needs **both**
`pi_bridge` (schedules) and `api_server` (sends).

---

## 1. One-time Pi setup

```bash
# a) System packages + I2C (for the ADS1115)
sudo apt update && sudo apt install -y python3-venv python3-pip mosquitto mosquitto-clients
sudo raspi-config nonint do_i2c 0          # enable I2C (reboot if it wasn't on)

# b) Clone the repo
git clone https://github.com/25006675-png/wattseye.git
cd wattseye

# c) Python environment + dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
#   torch is heavy and only needed for live NILM (WATTSEYE_NILM=1). The core
#   loop — AC clamp + occupancy + cutoff + coach + WhatsApp — does NOT need it.
#   To skip it on first run: pip install paho-mqtt scikit-learn joblib reportlab
#   adafruit-circuitpython-ads1x15
```

## 2. Configure `.env` (the part git does NOT bring)

`.env` is gitignored, so `git pull` never touches it — you set it up once and it
persists. Copy your laptop's `.env` to the Pi (scp/USB), or start from the
template:

```bash
cp .env.example .env
nano .env        # fill in the real values
```

Required for WhatsApp/Gemini:
- `META_ACCESS_TOKEN` — **use a permanent System User token** for the Pi, not the
  24h API-Setup token (that one expires daily).
- `META_PHONE_NUMBER_ID`, `META_RECIPIENT`, `GEMINI_API_KEY`, `WATTSEYE_LANG`.

Optional (hardware calibration — see step 4): `WATTSEYE_VOLTS_PER_VOLT`,
`WATTSEYE_AMPS_PER_VOLT`, `WATTSEYE_CAL_*`.

> ⚠️ A WhatsApp access token committed to git is a leak. Keep it only in `.env`.

## 3. Flash the ESP32 (`firmware/esp32_node/esp32_node.ino`)

In the Arduino IDE (libraries: PubSubClient, ArduinoJson, IRremoteESP8266), set
before flashing:
- `WIFI_SSID`, `WIFI_PASS`
- `MQTT_HOST` → the **Pi's LAN IP** (e.g. `192.168.0.50`)
- `USE_REAL_AC` → `false` sends a demo NEC frame; for a real cutoff, set `true`
  and include your AC brand's protocol (e.g. `#include <ir_Daikin.h>`).

Re-flash over USB whenever you change the `.ino` — `git pull` on the Pi does not
update the ESP32.

## 4. Calibrate the clamps (set in `.env`, no code edits)

With the rig powered (a qualified person must check mains wiring first), compare
the reported watts against a reference meter and trim via `.env`:

```ini
WATTSEYE_VOLTS_PER_VOLT=240.0     # mains volts per 1 V at ZMPT101B OUT
WATTSEYE_CAL_MAIN_SCALE=1.00      # multiply the whole-home reading to match
WATTSEYE_CAL_AC_SCALE=1.00        # multiply the AC-branch reading to match
```

See `HARDWARE_CONNECTION.md` §16. Accurate watts matter: the cutoff trigger
(`HIGH_POWER_WATTS = 700`) and every ringgit figure depend on them.

## 5. Run the live loop (four shells, or systemd)

```bash
mosquitto -v                                   # shell 1 (or run as a service)
python -m ML.sensing.ads1115_reader            # shell 2  (--simulate for no hardware)
python -m backend.pi_bridge                    # shell 3
python backend/api_server.py                   # shell 4  (serves :8080, starts WhatsApp daemon)
#   For live per-appliance NILM tiles: WATTSEYE_NILM=1 python -m backend.pi_bridge
```

## 6. Point the app at the Pi

```bash
flutter run --dart-define=WATTSEYE_API_BASE=http://<pi-ip>:8080
```
`api_server` binds `0.0.0.0`, so any device on the LAN can reach it. The AppBar
chip flips to "Live Pi" once `pi_bridge` is writing fresh `live_state.json`.

## 7. Verify

```bash
python -m backend.pi_bridge --self-test                 # decision + state logic
python -X utf8 -m ML.insights.coach.whatsapp --hello    # confirm Meta credentials
mosquitto_sub -t 'wattseye/#' -v                        # watch live MQTT traffic
```

---

## Updating after the first deploy

You edit on the **laptop**; the Pi pulls. No manual file copying.

```bash
# laptop
git add -A && git commit -m "…" && git push
# Pi
git pull
# then restart only the process you changed (Python does not hot-reload):
#   Ctrl-C it, then re-run its command from step 5.
```

- `.env` and runtime files (`live_state.json`, `_smart_rule.json`, `reminders.json`)
  stay on the Pi across pulls — they're gitignored.
- The **smart rule** values are re-read every tick, so changing the rule in the
  app needs no restart — only *code* changes do.
- **ESP32**: `git pull` brings the new `.ino`, but you must **re-flash over USB**.

## Optional: run as services

For 24/7 operation, wrap each process in a `systemd` unit with
`EnvironmentFile=/home/pi/wattseye/.env` and `Restart=on-failure`, instead of
four shells. (Units are not in the repo yet — add per your Pi user/paths.)

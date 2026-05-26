# Step 3 — Install & run WattsEye on the Pi

**Goal:** put the code on the Pi, install the dependencies (including the tricky
PyTorch), and run the three services — first in **simulate** mode (no sensors yet),
so the Pi is fully working before any hardware is attached.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md) §14.5,
[`../../plan/03_MACHINE_LEARNING.md`](../../plan/03_MACHINE_LEARNING.md) §15.

> 🟢 No mains. All over SSH from Step 2. ⏱️ ~45 min (PyTorch is the slow part).

---

## Prerequisite

You can `ssh pi@wattseye.local` (Step 2). Run everything below **in that SSH
session** (i.e. on the Pi).

## Step 3.1 — System packages + I²C + broker

```bash
sudo raspi-config        # Interface Options → I2C → Enable, then finish
sudo reboot              # reconnect with ssh after ~30 s
```

Reconnect, then:

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv i2c-tools git mosquitto mosquitto-clients
```

- `i2c-tools` → lets you detect the ADS1115 in Step 5.
- `mosquitto` → the MQTT broker the whole rig talks through.

## Step 3.2 — Let devices on the LAN reach the broker

The ESP32 (Step 6) connects over WiFi, so open Mosquitto to the LAN:

```bash
sudo tee /etc/mosquitto/conf.d/wattseye.conf >/dev/null <<'EOF'
listener 1883 0.0.0.0
allow_anonymous true
EOF
sudo systemctl enable --now mosquitto
sudo systemctl restart mosquitto
```

> `allow_anonymous true` is **demo-only** — fine on a private LAN, not for production.

## Step 3.3 — Get the code

```bash
git clone <your-repo-url> wattseye && cd wattseye
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
```

> Replace `<your-repo-url>` with the actual repo URL. The models ship **inside the
> repo** (`ML/NILM/*.pth`, `ML/anomaly/*.joblib`, `ML/routine/*.joblib`) — there's
> no separate "upload models" step.

## Step 3.4 — PyTorch on the Pi (the one fiddly step)

`backend/requirements.txt` lists `torch`. On a **64-bit** Pi OS (you chose that in
Step 2), `pip install` usually finds an `aarch64` wheel. Verify:

```bash
python -c "import torch; print(torch.__version__)"
```

If that errors:
1. Confirm 64-bit: `uname -m` → must say `aarch64`.
2. Fallback: `sudo apt-get install -y python3-torch` (older but works), then use the
   system Python, **or** find a community `aarch64` wheel for your exact Python.
3. CPU inference is fine — the NILM models are small Transformers; **no GPU needed**.

Benchmark when it imports:
```bash
python ML/NILM/test_nilm_inference.py --all   # see plan/03 §15 for the speed budget
```

## Step 3.5 — Prove the logic on the Pi (no sensors)

```bash
python -m backend.pi_bridge --self-test
python -m ML.sensing.ads1115_reader --simulate --no-mqtt --count 3
python ML/sensing/power_math.py
```

All three should print results and exit cleanly — same checks that passed on your
laptop, now on the Pi.

## Step 3.6 — Run the three services (simulate mode)

Open **three SSH sessions** to the Pi (or use `tmux`). In each, `cd wattseye &&
source .venv/bin/activate` first.

```bash
# session A — the API the app talks to
python backend/api_server.py

# session B — the brain
python -m backend.pi_bridge

# session C — simulated sensor (drop --simulate in Step 5 for real readings)
python -m ML.sensing.ads1115_reader --simulate
```

Check from your **laptop** (replace IP if `.local` doesn't resolve):

```powershell
Invoke-RestMethod http://wattseye.local:8080/api/dashboard | ConvertTo-Json -Depth 5
```

✅ Success: the JSON shows **`"source": "live_pi"`** and `live_power_w` changes each
call. The Pi is now serving the live pipeline — on simulated data for now.

## Step 3.7 — (Optional) Make it always-on with systemd

For a demo that survives reboots/logout, wrap each service in a systemd unit
(`Restart=always`, `After=mosquitto.service`,
`WorkingDirectory=/home/pi/wattseye`,
`ExecStart=/home/pi/wattseye/.venv/bin/python -m backend.pi_bridge`). One unit each
for `api_server`, `pi_bridge`, `ads1115_reader`. See `HARDWARE_CONNECTION.md` §14.5.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install torch` fails | See Step 3.4 fallbacks; confirm `aarch64` |
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate` |
| `/api/dashboard` not reachable from laptop | Use the Pi's IP; check `api_server.py` is running; same network |
| `"source":"live_pi"` missing | All of A+B+C must run; the reader must keep publishing (live_state is fresh ~15 s) |
| ESP32 can't connect later | Confirm Step 3.2 listener `0.0.0.0` + `mosquitto` active |

---

← Prev: [Step 2 — Flash & set up the Pi](02_pi_setup.md) ·
Next: [Step 4 — Breadboard circuits](04_breadboard_circuits.md) →

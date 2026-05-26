# Step 1 — Laptop software loop (no hardware)

**Goal:** run the **entire WattsEye live pipeline on your laptop**, with a real
MQTT broker, before any hardware exists. This proves the software chain end-to-end
and is the fastest possible "it works" win.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md) §14,
§14.4.

> 🟢 Pure software. No hardware at all. ⏱️ ~30 min (most of it installing Mosquitto).

---

## The pipeline you're about to run

```
ads1115_reader.py --simulate ──(MQTT wattseye/power)──► pi_bridge.py ──► live_state.json
                                                                            │
                                                          api_server.py reads it
                                                                            │
                                                  GET /api/dashboard → "source":"live_pi"
```

Four programs, four terminals:

| Terminal | Program | Role |
|---|---|---|
| A | **Mosquitto** | the MQTT broker (message bus) |
| B | `python -m backend.pi_bridge` | the "Pi brain": decisions + writes live_state.json |
| C | `python -m ML.sensing.ads1115_reader --simulate` | fake sensor: publishes power 1×/sec |
| D | `python backend/api_server.py` | the app's API; serves live_state.json when fresh |

---

## Step 1.0 — Quick no-broker checks (sanity, 1 min)

No install needed — just confirm the logic is healthy:

```powershell
python -m backend.pi_bridge --self-test
python -m ML.sensing.ads1115_reader --simulate --no-mqtt --count 3
python ML\sensing\power_math.py
```

All three should print results and exit cleanly. Now for the *full* loop with a
real broker:

## Step 1.1 — Install the Python MQTT client

```powershell
python -m pip install paho-mqtt
# or the full set:
python -m pip install -r backend\requirements.txt
```

## Step 1.2 — Install Mosquitto (the broker) on Windows

1. Download the **Windows x64 installer** from <https://mosquitto.org/download/>.
2. Run it (default path `C:\Program Files\mosquitto\`).
3. The installer may register Mosquitto as an **auto-starting service**. For this
   task we'll run it **manually with logging**, so free the port first:

   ```powershell
   Get-Service mosquitto -ErrorAction SilentlyContinue
   Stop-Service mosquitto -ErrorAction SilentlyContinue   # if it shows Running
   ```

> Prefer zero fuss? Leave the service running and **skip Terminal A** — the broker
> is already up on `localhost:1883`.

## Step 1.3 — Terminal A: start the broker (verbose)

```powershell
& "C:\Program Files\mosquitto\mosquitto.exe" -v
```

## Step 1.4 — Terminals B, C, D: start the services

Three more PowerShell windows, each in the repo root (`C:\Users\user\wattseye`):

```powershell
python -m backend.pi_bridge                       # Terminal B
python -m ML.sensing.ads1115_reader --simulate    # Terminal C
python backend\api_server.py                       # Terminal D
```

## Step 1.5 — Confirm the loop is live

```powershell
Invoke-RestMethod http://localhost:8080/api/dashboard | ConvertTo-Json -Depth 5
```

✅ Success: the JSON contains **`"source": "live_pi"`** and `live_power_w` **changes**
each time you re-run it. (If you see fixed demo numbers and no `live_pi`, the bridge
isn't receiving — see troubleshooting.)

## Step 1.6 — (Optional) watch the raw MQTT traffic

```powershell
& "C:\Program Files\mosquitto\mosquitto_sub.exe" -h localhost -t "wattseye/#" -v
```

A `wattseye/power` message ticks by once per second.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: paho` | `python -m pip install paho-mqtt` |
| Terminal A: `Address already in use` | The Mosquitto **service** holds 1883 — `Stop-Service mosquitto`, or skip Terminal A |
| `/api/dashboard` shows demo numbers | Bridge not receiving: confirm A+B+C all running; keep the reader running (live_state is fresh ~15 s) |
| Want to stop everything | Ctrl+C each terminal; `Start-Service mosquitto` to restore the auto service |

---

## Note

This same code runs on the **Pi** in [Step 3](03_pi_run.md) — the laptop loop is
just the rehearsal. The Pi becomes the real broker the ESP32 connects to (Step 6).

---

Next: [Step 2 — Flash & set up the Raspberry Pi](02_pi_setup.md) →

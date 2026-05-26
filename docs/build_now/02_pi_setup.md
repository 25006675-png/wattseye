# Step 2 — Flash & set up the Raspberry Pi

**Goal:** get the Pi booted, on WiFi, and reachable from your laptop over SSH, so
you can run the WattsEye services on it.

**Reference:** [`../../HARDWARE_CONNECTION.md`](../../HARDWARE_CONNECTION.md) §14.5.

> 🟢 No mains, no soldering. Just the Pi, the SD card, and a proper power supply.
> ⏱️ ~30 min (mostly the SD card write).

---

## What you need

- **Raspberry Pi 4** + the **SD card** (microSD; use the SD adapter to flash it)
- A **proper 5 V / 3 A USB-C power supply** — **not** a laptop USB port (a laptop
  port under-powers the Pi 4 and causes crashes/under-voltage)
- Your laptop with an SD card reader
- Your **2.4 GHz WiFi** name + password (the Pi's onboard WiFi is 2.4 GHz)

---

## Step 2.1 — Flash the SD card with Raspberry Pi Imager

1. Download **Raspberry Pi Imager** from <https://www.raspberrypi.com/software/>
   and install it.
2. Insert the SD card (in its adapter) into your laptop.
3. Open Imager:
   - **Choose Device** → *Raspberry Pi 4*
   - **Choose OS** → *Raspberry Pi OS (64-bit)* — pick **64-bit** so PyTorch has an
     `aarch64` wheel later (Step 3).
   - **Choose Storage** → your SD card. ⚠️ Double-check it's the card, not a USB
     drive — Imager **erases** it.

## Step 2.2 — Pre-configure SSH + WiFi (the important bit)

Before writing, click **Next → Edit Settings** (the ⚙️ / "customise" prompt) and set:

- **Hostname:** `wattseye` (so you can reach it at `wattseye.local`)
- **Enable SSH** → *Use password authentication*
- **Username and password:** e.g. `pi` / a password you'll remember
- **Configure wireless LAN:** your WiFi **SSID + password**, and **Wireless LAN
  country** (e.g. `MY`)
- **Locale / timezone:** your region

> This step is what lets you connect **headless** (no monitor/keyboard). Skipping it
> means the Pi boots with no way in.

Then **Save → Write → Yes**. Wait for "Write Successful", then eject the card.

## Step 2.3 — Boot the Pi

1. Insert the SD card into the Pi.
2. Plug in the **5 V/3 A USB-C** power supply.
3. Watch the LEDs: red = power, green flickers = reading the SD card. Give it
   **~60 seconds** to boot and join WiFi.

> ⚠️ If you only see a **steady red LED and no green flicker**, the card didn't
> flash correctly or isn't seated. If you see a **lightning-bolt** on a monitor,
> the power supply is too weak — use a proper 3 A one.

## Step 2.4 — Connect from your laptop (SSH)

Windows 11 has SSH built in. In PowerShell:

```powershell
ping wattseye.local
ssh pi@wattseye.local
```

- First connection asks *"Are you sure you want to continue connecting?"* → type
  `yes`.
- Enter the password you set in Step 2.2.
- Success = your prompt changes to something like `pi@wattseye:~ $`. **Every command
  now runs on the Pi.**

## Step 2.5 — Confirm it's healthy

On the Pi:

```bash
hostname -I            # shows the Pi's IP — note it; the ESP32 will use it (Step 6)
uname -m               # aarch64 confirms 64-bit OS
```

🎉 You now have remote control of the Pi. Keep this SSH window open for Step 3.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ping wattseye.local` fails | Wait longer (first boot is slow); confirm WiFi creds in Imager; laptop + Pi on same network; try the IP from a monitor or your router's device list |
| `ssh: connection refused` | SSH wasn't enabled in Imager — re-flash with "Enable SSH" ticked |
| Asks for password but rejects it | Wrong username/password from Imager; re-flash to reset |
| Pi keeps rebooting / red LED only | Weak power supply (use 5 V/3 A); re-seat or re-flash the SD card |
| `wattseye.local` won't resolve but IP works | mDNS issue — just use `ssh pi@<ip>` from `hostname -I` |

---

← Prev: [Step 1 — Laptop software loop](01_laptop_software_loop.md) ·
Next: [Step 3 — Install & run WattsEye on the Pi](03_pi_run.md) →

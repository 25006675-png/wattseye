# 02 — Hardware: What We Need and How It Works

## 1. Purpose of this file

This file explains the physical parts of WattsEye.

It focuses on:

- What hardware we need
- Why each part exists
- How each part connects
- What safety rules matter

This file is written for beginners.

## 2. Full hardware list

### Electricity sensing hardware

- **CT clamp sensor x 2** (such as SCT-013-030)
  - Clamp #1 — Main feeder (whole-home NILM input)
  - Clamp #2 — Dedicated AC circuit (direct AC measurement)
- Voltage sensor module, such as ZMPT101B
- ADS1115 ADC breakout board (4 channels — supports both clamps + voltage)
- Signal conditioning components (one set per CT clamp, so x 2):
  - Burden resistor
  - Voltage divider resistors
  - Capacitor
- Raspberry Pi 4
- Jumper wires
- Breadboard or PCB

### Control and occupancy hardware

- ESP32 development board (for mmWave reading + IR transmit)
- LD2410 mmWave sensor
- IR LED (transmits AC off command)
- NPN transistor, such as 2N2222 (drives IR LED)
- Resistors for transistor and LED circuit

### AC-cutoff demo block (new for hybrid)

This block lets the IR command actually cut power to the AC simulator on stage. In a real home this is not needed — the real AC unit's own IR receiver responds to the signal.

- IR receiver module (such as TSOP1838)
- 5V single-channel relay module (opto-isolated, rated for mains switching)
- NPN transistor + resistors (drives the relay from the IR receiver output)
- Optional: small MCU (Arduino Nano) if not using the analog receiver-to-relay path

### Demo rig hardware

- Clear or closed plastic enclosure
- Power inlet cable
- Outlet bank or extension socket
- Inline fuse
- Terminal blocks (with split bus for general branch + AC branch)
- Live, neutral, and earth wiring
- Strain relief for cable
- "AC SIMULATOR" outlet + label tape (so it's clear what the dedicated AC outlet represents)

## 3. Safety warning

The demo box involves mains electricity.

In Malaysia, this is around 240V AC.

This can be dangerous.

Important rules:

- Do not leave live wires exposed.
- Put high-voltage parts inside a closed enclosure.
- Use an inline fuse.
- Connect earth properly.
- Separate high-voltage wiring from low-voltage electronics.
- Use strain relief so cables cannot be pulled loose.
- Ask a lecturer, lab technician, or electrician to check before powering on.

The software can be tested safely first. The mains wiring must be treated carefully.

## 4. CT clamp

### What it is

A CT clamp is a plastic clip that wraps around a wire.

It does not cut the wire.

It does not directly touch the copper conductor.

### Why we need it

It measures current safely.

When electricity flows through a wire, it creates a magnetic field.

The CT clamp senses this magnetic field.

More current means a stronger magnetic field.

### Where it goes

WattsEye uses **two CT clamps**, placed at different points:

- **Clamp #1 (Main / NILM)** — wraps around the main live wire just after the inlet fuse. Sees total household current.
- **Clamp #2 (Dedicated AC)** — wraps around the live wire of the dedicated AC branch (downstream of the terminal block, before the AC outlet). Sees only the AC's current.

Each clamp should only go around the live wire, not live and neutral together.

In a real home installation, both clamps go inside the DB box: one on the main feeder, one on the AC circuit breaker output wire. No rewiring of the home is needed because the AC already has its own dedicated wire by code (MS IEC 60364).

### Why two clamps and not one

- The main clamp sees everything combined — needed for whole-home NILM disaggregation.
- The AC clamp sees only the AC — needed because inverter ACs have no clean NILM signature, so AI alone cannot reliably detect them.
- Together: subtract the AC clamp reading from the main clamp signal to get a cleaner NILM input for non-AC appliances. Also compare the NILM AC estimate to the direct AC reading to validate the model live.

### What happens if we remove a clamp

- Remove Clamp #1: lose whole-home NILM. Only AC consumption is known.
- Remove Clamp #2: lose reliable AC detection (especially for inverter ACs), lose the live validation moment, and the live IR cutoff demo cannot be confirmed on the dashboard.

## 5. Why the CT clamp signal needs conditioning

The CT clamp produces a small AC signal.

This signal moves positive and negative.

But the electronics can only read safe positive voltages.

So we need a signal conditioning circuit.

The circuit does three main things:

1. Converts the clamp signal into a measurable voltage.
2. Shifts the signal upward so it stays positive.
3. Keeps the signal inside a safe voltage range.

## 6. Burden resistor

### What it does

The CT clamp output behaves like a current signal.

The ADC reads voltage, not current.

The burden resistor converts that current signal into a voltage signal.

### Simple analogy

The clamp gives “flow.”

The resistor turns that flow into “pressure” that the chip can measure.

## 7. Voltage divider

### What it does

The voltage divider creates a safe midpoint voltage.

For a 3.3V system, the midpoint is usually around 1.65V.

This shifts the AC signal upward.

### Why it matters

Without this, part of the signal may go negative.

The ADC cannot read negative voltage safely.

## 8. Capacitor

### What it does

The capacitor helps combine the moving clamp signal with the steady midpoint voltage.

This allows the final signal to wobble around 1.65V instead of 0V.

## 9. ADS1115 ADC

### What it is

ADS1115 is an analog-to-digital converter.

### Why we need it

The Raspberry Pi does not have analog input pins.

The clamp and voltage sensor produce analog signals.

The ADS1115 converts those analog signals into digital numbers.

### How it connects to Raspberry Pi

Typical connection:

```text
ADS1115 VDD → Raspberry Pi 3.3V
ADS1115 GND → Raspberry Pi GND
ADS1115 SDA → Raspberry Pi GPIO 2
ADS1115 SCL → Raspberry Pi GPIO 3
Clamp #1 (main feeder) conditioned signal → ADS1115 A0
Voltage sensor output                      → ADS1115 A1
Clamp #2 (dedicated AC) conditioned signal → ADS1115 A2
(ADS1115 A3 reserved for future expansion, e.g. additional dedicated circuit)
```

## 10. ZMPT101B voltage sensor

### What it is

ZMPT101B is a voltage sensor module.

### Why we need it

To calculate power we need both voltage and current. The textbook formula is:

```text
Power = Voltage × Current
```

That formula is exact for DC. For 50 Hz mains it is more nuanced — see §10a below.

The CT clamp gives current information.

The ZMPT101B gives voltage information.

### Why not measure 240V directly?

Because 240V is dangerous and too high for electronics.

The ZMPT101B safely converts it into a small signal.

## 10a. What the ADS1115 + ZMPT101B can actually measure

Honest accounting of the sampling pipeline:

- **ADS1115 max sample rate**: 860 samples per second total, shared across however many channels the multiplexer scans.
- **Our setup uses 3 channels** (A0 = main current, A1 = voltage, A2 = AC current), so real-world throughput is about **200-300 samples per second per channel** after mux switching overhead.
- **Malaysian mains is 50 Hz**, so one full sine cycle takes 20 milliseconds. At 250 SPS that gives us about **5 samples per cycle** — enough to estimate RMS magnitude reliably, not enough to resolve the phase relationship between voltage and current.

What this means in practice:

| We can compute | We cannot compute reliably |
|---|---|
| Vrms (RMS voltage) | True real power for non-resistive loads |
| Irms per clamp (RMS current) | Power factor of an inverter AC |
| Apparent power S = Vrms × Irms (units: VA) | Reactive power Q |
| Energy estimate based on S over time | Real-time PF for variable loads |

For **resistive demo loads** (kettle, hair dryer, iron, incandescent lamp) the power factor is ≈1.00, so apparent power equals real power within ~2%. The dashboard numbers you see live during the demo are accurate to within calibration error.

For **inductive or switching loads** (LED lamp, fridge compressor, inverter AC) the power factor drops to 0.6-0.9 and apparent power overstates real watts by 10-40%. WattsEye applies a per-appliance power-factor correction at the insight layer using calibration constants stored in `ML/sensing/power_math.py`. This is documented in plan 04 §5.

### When to upgrade the sensing chain

The ADS1115 is fine for the prototype. Two upgrade paths exist if production accuracy matters:

| Upgrade | Cost | What it buys you |
|---|---|---|
| Faster ADC (MCP3008 over SPI, ~200 kSPS) | RM 10-25 | Enough samples per cycle to compute true real power in software, including power factor |
| Dedicated energy-metering IC (PZEM-004T or ADE7953) | RM 30-60 | Chip returns V, I, W, PF, and accumulated energy directly over UART/I2C — no software RMS math required |

Neither is needed for the demo. Both are documented here so the next team knows the path forward.

## 11. Raspberry Pi

### What it is

A Raspberry Pi is a small computer.

### What it does in this project

It handles:

- Reading ADS1115 data
- Calculating power
- Running AI models
- Storing readings
- Hosting dashboard
- Sending WhatsApp alerts
- Communicating with ESP32

## 12. ESP32

### What it is

ESP32 is a small microcontroller board with WiFi.

### What it does in this project

It handles:

- Reading the mmWave sensor
- Sending IR commands to AC
- Receiving commands from Raspberry Pi

## 13. LD2410 mmWave sensor

### What it is

A presence sensor.

It detects whether someone is in the room.

### Why we use mmWave instead of normal motion sensor

Normal PIR motion sensors mainly detect movement.

If a person sits still, a PIR sensor may think the room is empty.

mmWave can detect smaller movements, including breathing-like movement.

This is better for room occupancy.

## 14. IR LED and transistor

### What it does

The IR LED sends infrared light signals like an AC remote. In a real home, this signal is received directly by the AC unit's built-in IR receiver and switches the AC off (or to standby).

### Why we need a transistor

The ESP32 pin is not strong enough to drive the IR LED brightly by itself.

The transistor acts like a switch.

The ESP32 controls the transistor, and the transistor allows more current to pass through the IR LED.

### Hardware is fine, protocol matters

The IR LED + 2N2222 hardware is correct as-is for both the demo rig and a real Malaysian home. The thing that changes between the two is the **firmware payload**, not the parts:

- **Demo rig (TSOP1838 + relay path)**: any 38 kHz IR carrier opens the relay. No brand code needed. Plain `tone(38000)` from the ESP32 works.
- **Real home with an inverter AC** (Daikin, Panasonic, Midea, York, Hisense, etc.): the AC's onboard IR receiver expects a brand-specific state frame containing mode, setpoint, fan, and the power bit. A generic 38 kHz pulse will be ignored. Use the `IRremoteESP8266` Arduino library and call the brand's `.off()` (e.g. `IRDaikinESP`, `IRPanasonicAc`, `IRMideaAC`) — or capture the existing remote's "off" frame with a TSOP1838 in record mode and replay it.

No new components need to be purchased to support real ACs. The bottleneck is brand-code selection in firmware, not hardware.

## 14a. IR receiver + relay (demo rig only)

### What it does

The demo rig does not include a real AC unit, so the IR LED has nothing to control on its own. To demonstrate the cutoff on stage, we add an IR receiver paired with a relay:

- The TSOP1838 IR receiver detects the 38 kHz IR carrier from the IR LED.
- Its output triggers a transistor that drives a relay.
- The relay's mains-side contact is wired in series with the AC-simulator outlet.
- When the IR signal arrives, the relay opens and cuts power to the AC simulator.

This block is purely for the live demo. In a production install on a real Malaysian home, the existing AC unit handles the IR command directly and the relay block is not needed.

### Two ways to drive the relay

- **Analog path (simpler, recommended)**: TSOP1838 output → transistor → relay coil → relay contact opens. No MCU required. Lower cost (~RM 20 less), fewer failure points. Downside: relay fires on any 38 kHz IR signal — keep the IR LED aimed away during unrelated tests.
- **MCU path**: TSOP1838 output → Arduino Nano (decodes protocol) → relay. More selective, but more parts.

For the prototype, the analog path is sufficient and lower-risk.

## 15. Demo box build concept

The demo box simulates a home distribution system with two branches — one for general appliances and one dedicated to the AC. This mirrors how a real Malaysian DB box is wired (general "power sockets" circuit + dedicated AC circuit).

It should contain:

```text
Power inlet (13A plug)
↓
Inline fuse (10A)
↓
Main CT clamp #1 wraps the live wire here  (whole-home / NILM input)
↓
Terminal block (the "mini DB box")
├──► General branch wire ──► General outlets (kettle, lamp, fan, hair dryer, etc.)
└──► AC branch wire
       ↓
       AC CT clamp #2 wraps the live wire here  (direct AC measurement)
       ↓
       Relay contact (controlled by IR receiver)
       ↓
       "AC SIMULATOR" outlet  (plug a hair dryer or small heater here as AC proxy)
```

The voltage sensor connects across live and neutral after the fuse.

Low-voltage sensor wires go out to the electronics area.

The "AC SIMULATOR" outlet should be physically labeled so judges and teammates understand that this outlet represents the AC circuit in a real home.

## 16. Hardware testing order

Recommended order:

1. Build low-voltage circuits first without mains power.
2. Test Raspberry Pi and ADS1115 using simple known signals (test both clamp channels A0 and A2).
3. Test ESP32 and mmWave sensor.
4. Test ESP32 and IR LED transmit using a phone camera (IR shows up as visible light on most phone cameras).
5. Test IR receiver + relay block standalone: aim IR LED at TSOP1838, confirm the relay clicks open.
6. Build demo box wiring with split bus (general branch + AC branch).
7. Ask someone qualified to check wiring.
8. Power on with caution.
9. Test general branch with one appliance — confirm only Clamp #1 sees it.
10. Test AC branch with one appliance — confirm both Clamp #1 and Clamp #2 see it, and the relay can cut its power on IR command.
11. Compare measured power with expected appliance rating (calibration).

## 17. Common beginner mistakes

### Mistake 1: Clamping around both live and neutral

If the clamp wraps around both live and neutral, the magnetic fields may cancel out.

The reading may become near zero.

### Mistake 2: Feeding raw clamp signal directly to electronics

The signal may go negative or exceed safe range.

Use signal conditioning.

### Mistake 3: Forgetting voltage measurement

Current alone is not enough for accurate watt calculation.

### Mistake 4: Mixing high-voltage and low-voltage areas

Keep mains wiring away from Raspberry Pi, ESP32, and breadboard.

### Mistake 5: No calibration

Even if the circuit works, readings may not match real watts.

Use known appliances to calibrate.

## 18. Hardware summary

The hardware does not magically identify appliances.

It only produces electricity data.

The AI does the appliance identification.

The hardware goal is:

```text
Safely convert real electricity usage into clean digital power readings.
```

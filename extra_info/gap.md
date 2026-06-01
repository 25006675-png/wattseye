Inspected the full Flutter app (2,420 lines), api.dart, the backend routes, and the Pi-side code. Here's what I found across all three.

# 1. UI/UX — what I'd change (hackathon, AI era)

The app is competent Material-3, but in an era where every team ships a polished AI-built UI, "5 clean tabs" is the floor. The wins are about hierarchy, integrity, and the one signature interaction — not more screens.

## a. Money-first hierarchy is inverted.

The dashboard hero is LivePowerCard → "1.42 kW." Users don't think in kW; they think in ringgit. Lead with today's cost + projected bill + "RM avoidable right now," and demote kW to a secondary stat. This is the same ringgit-over-carbon-over-watts point — the kW-as-hero is an engineer's instinct, not a user's.

## b. The "Turn off" button is a fake snackbar

(main.dart:636 → _snack(context, 'AC turn-off command sent')).

It calls nothing.

In a live hardware demo, a button that pretends to act is a credibility landmine — if a judge taps it and the hair dryer keeps running, you're done.

Either wire it to the real cutoff or remove it and make WhatsApp the only action button (which is wired). Integrity > feature.

## c. Design for the sparse live reality.

Offline/demo shows 12 cards; live data realistically yields 1–2. Right now the Coach page is built around a 12-card wall that will look empty and broken in live mode.

Design the 1–2-card state to look intentional ("Your home is running clean right now"), not like a failure.

## d. Provenance belongs per-card, not just one global chip.

The Demo data / Live Pi chip (main.dart:490) is your single most important honesty signal, but one global chip can't express "this card is live, those are replay."

Tag each card.

This is exactly the live-vs-replay labeling we discussed — it's the difference between "honest" and "got caught."

## e. The explainable coach card is your crown jewel — make it the spine, and show the loop learn.

The "Why this appeared" + math + impact is genuinely differentiated and auditable.

But dismissal (_markAction) just mutates state silently.

Make dismissal visibly re-rank ("we'll show this less, here's what's next") — that's what lets you honestly claim "it learns from rejection" instead of "tips feed."

## f. Your two unique features are buried and hardcoded.

The 1,500 kWh cliff and ToU comparator are the things no foreign product has — and they're static text on the Bill page.

Give the cliff a visual gauge ("you are here → cliff at 1500") and ToU a side-by-side.

Memorable + uniquely Malaysian.

## g. Cut History + Profile from the demo path.

They're filler that eats judge time and invites "is this real?" questions.

Five tabs says "we built an app"; one hero flow says "we solved a problem."

## h. "Bilingual" is a deck claim with zero UI evidence — the app is English-only.

Either show one BM string/toggle, or move the bilingual proof to the WhatsApp thread (its more authentic home) and don't claim it in the app.

# 2. UI logic NOT wired to backend (hardware excluded)

The backend serves more than the app consumes. Confirmed gaps:

| UI surface | Backend endpoint | Status |
|---|---:|---|
| Bill page | /api/bill exists (projected, kWh, effective sen, ToU) | Not called — fully hardcoded |
| History page | /api/history exists (daily cost) | Not called — static const HistoryPage() |
| Weather (anywhere in UI) | /api/weather exists (real Open-Meteo) | Never called (only feeds coach server-side) |
| Monthly PDF report | /api/report/monthly exists (reportlab) | No UI button to view/download |
| Live NILM inference | /api/ml/nilm/infer, /api/ml/status exist | App only reads nilm_model_count; no inference UI |
| "Turn off" AC | No API route at all (cutoff is MQTT-only) | Cosmetic snackbar |

Wired correctly:

- dashboard
- coach cards (GET)
- coach action (POST do/remind/dismiss)
- integration status
- WhatsApp send

The offline fallback to hardcoded _coachCards is good resilient design.

Net: Bill and History are the two pages most likely to be probed ("is this your real data?") and they're the two that are 100% hardcoded despite the backend already serving the data.

Wiring those two is ~30 lines in api.dart + the page constructors, and it's the highest-credibility-per-effort fix in the app.

# 3. Can the Pi run the codebase? Is it complete?

Mostly yes for the sensing→cutoff→dashboard loop; no for live appliance breakdown.

## What works:

- ads1115_reader.py imports cleanly off-Pi — board/busio/paho are lazy-imported, and --simulate / --no-mqtt let you run the whole pipeline on a laptop. On the Pi it needs adafruit-circuitpython-ads1x15 (in requirements.txt, correctly ARM-gated) + paho-mqtt + I2C enabled.
- pi_bridge.py self-test passes (I ran python -m backend.pi_bridge --self-test → PASSED, cutoff fires once, debounces, re-arms, writes valid dashboard JSON).
- api_server.py is stdlib http.server — runs anywhere.
- Chain is complete:

mosquitto → reader → bridge → api → app

and docs/build_now/02–03 cover Pi setup/run.

## Real gaps:

### 1. Live NILM is not in the pipeline.

pi_bridge lumps everything non-AC into one "other" bucket (pi_bridge.py:156) — there's no per-appliance disaggregation at runtime.

The faithful electricity_model.py exists but nothing calls it in the live loop.

So on the Pi you get:

- total
- AC
- other

not kettle/fridge tiles.

This is the piece I keep offering to wire.

### 2. Calibration constants are placeholders.

VOLTS_PER_VOLT = 240 # placeholder

plus the SCT-013 scale.

It will run and publish watts, but the numbers are uncalibrated until you do build_now/08.

Don't trust the live wattage before calibration.

### 3. requirements.txt lists flask>=3.0 which is unused.

The API is stdlib http.server.

Harmless but misleading — drop it.

### 4. No process orchestration.

No systemd units or single launch script currently bring up:

- broker
- reader
- bridge
- api

together.

The run doc lists manual steps.

Minor, but a one-shot run_pi.sh would de-risk the demo.

---

# Highest-leverage fixes, ranked

1. Wire Bill + History to their existing endpoints  
   Cheap, kills the “is it real?” probe.

2. Remove or wire the fake Turn-off button  
   Biggest integrity fix.

3. Money-first dashboard + per-card provenance  
   Better judge comprehension.

4. Wire live NILM → per-appliance tiles + events  
   Unlocks live breakdown and real coach cards from bench log.

Want me to do #1 and #2 now (pure software, no hardware needed), and/or #4 (the live NILM wiring into pi_bridge)?
# WattsEye Coach Loop — Pitch Reference

The one-loop story behind the "Cut the bill" pillar. Grounded in the actual code
(`ML/insights/coach/`, `backend/snapshot_builder.py`) so it doubles as Q&A defense.

**One line:** *11 typed signals in → the correlator composes them into 1 of 12
recommendation types → the tariff engine prices it in ringgit → the ranker decides
what surfaces → your reply teaches it. One closed loop.*

The intelligence is in the **composition**, not any single model. Each signal is
cheap and narrow; the value is the chain that joins them into one evidenced,
priced, rankable action — auditable line by line.

---

## Stage 1 — DETECT: the 11 signals

Every signal emits a **typed fact with a number + confidence**, never a sentence.
The coach reads them as a `HomeSnapshot` (`situations.py`); it never touches raw
data. Built by `backend/snapshot_builder.py` (`from_live_state` / `from_history`).

### Measured — direct truth (×3, not ML)
| Signal | Emits | Source |
|---|---|---|
| Dedicated AC clamp | Exact AC watts (no inference) | CT clamp on AC branch |
| Main feeder clamp | Total whole-home watts | CT clamp at DB box |
| mmWave occupancy | `home/away/asleep` + since when | LD2410 sensor |

### Learned — our ML (×4)
| Signal | Emits | Source |
|---|---|---|
| **NILM transformer** | Per-appliance watts + on/off (e.g. `kettle 2050 W, ON`) | `ML/NILM/*.pth` (ELECTRIcity) |
| **Isolation Forest** | Anomaly score for a recent event (e.g. `-0.42`) | `ML/anomaly/isolation_forest.py` |
| **K-Means** | Current daily phase: morning/work/evening/sleep | `ML/routine/kmeans_phases.py` |
| **Linear Regression** | Appliance health residual (expected vs actual duty) | `ML/anomaly/appliance_health_regression.py` |

### Context — external grounding (×4, not ML)
| Signal | Emits | Source |
|---|---|---|
| Routine baseline | "AC usually on 19:00–23:00", standby level, peak-window kWh fraction | statistics over history |
| Weather | Today temp/max, hot days >33 °C next 7, hot-day AC uplift % | `coach/weather.py` (Open-Meteo, 9 cities, 1h cache) |
| TNB RP4 tariff | kWh → RM (generation/capacity/network, EEI, AFA, 1500 cliff, ToU) | `coach/../tnb_tariff.py` (deterministic math) |
| ST efficiency registry | Efficient-class watts + replacement cost + URL for an inefficient load | `coach/efficiency_registry.py` + `.csv` |

> Pitch wording: **"11 signals, 4 of them ML."** Never imply 11 sensors or 11 AI
> models. If pressed: *"a signal = one typed input the correlator fuses."*

---

## Stage 2 — COMPOSE: the correlator

`correlator.py`. A **deterministic rules layer** that joins signals into a named
**Situation** = one of the 12 archetypes, with its evidence and raw metrics.

One fact alone is rarely actionable; joined facts are. The correlator asks:
*"do I have enough independent evidence to claim something specific?"*

```
IF   occupancy = away
AND  AC watts > 800 for ≥ 10 min          (dedicated clamp / NILM)
AND  phase = work                          (K-Means)
AND  AC unusual at this hour               (routine baseline)
THEN Situation = left_on_empty  (severity: high)
     evidence  = [the 4 facts above, with timestamps]
     joint_confidence = combine(input confidences)
```

**Why it's not "just rules":** the inputs are ML/sensor-derived. Rules with no ML
have nothing to join; ML with no rules has no claim to make. The correlator is
where they meet. Source-attribution rule: any AC evidence line names the
**Dedicated CT clamp**, other appliances stay attributed to **NILM**.

### Per-card trigger logic (exact, from `correlator.py`)

Each detector is a pure function returning 0+ Situations. Thresholds are
centralised constants at the top of `correlator.py` — auditable line by line.
Peak window = **14:00–22:00 weekdays** (TNB ToU).

**Family A — Waste**

- **#1 `left_on_empty`** — *Fires when:* `occupancy = away` for **≥ 20 min** AND an
  active appliance draws **≥ 200 W** AND the current hour is **not** in that
  appliance's `expected_on_hours` (routine baseline). Loops over every active
  appliance.
  *Severity:* `high` if empty **≥ 45 min** and **≥ 800 W**, else `medium`.
  *Evidence:* Occupancy + power-source (Dedicated CT clamp for AC, else NILM) +
  K-Means phase + routine baseline.

- **#2 `phantom_standby`** — *Fires when:* overnight minimum load
  **≥ 30 W**. *Severity:* `high` if **≥ 80 W**, else `medium`.
  *Evidence:* NILM minimum-window base load + K-Means sleep phase.

- **#3 `simultaneous_peak_load`** — *Fires when:* currently in peak window AND
  **≥ 2** appliances each **> 500 W** AND combined **≥ 2500 W**.
  *Severity:* `medium`. *Evidence:* NILM concurrency + ToU schedule.

**Family B — Tariff**

- **#4 `tou_switch`** — *Fires when:* user **not** on ToU AND off-peak share of
  last-30-day kWh **≥ 60 %**. *Severity:* `medium`.
  *Evidence:* routine engine off-peak fraction + TNB tariff (ToU vs standard).

- **#5 `rp4_tier_cliff`** — *Fires when:* projected month-end kWh in the band
  **1420 → 1700** (within 80 below the 1500 cliff, up to 200 over).
  *Severity:* `high` if already over 1500, else `medium`.
  *Evidence:* cost engine projection + TNB RP4 (27.03→37.03 sen step).

- **#6 `peak_window_shift`** — *Fires when:* pattern leans peak-heavy
  (on ToU, or peak fraction ≥ 0.5) AND **≥ 3** schedulable runs
  (dishwasher / washer / dryer / water_heater) started in the peak window across
  recent events. *Severity:* `medium`. *Evidence:* NILM event log + ToU schedule.

**Family C — Forecast**

- **#7 `bill_trending_high`** — *Fires when:* projected kWh ÷ 3-month-avg kWh
  **≥ 1.15**. *Severity:* `high` if **≥ 1.25**, else `medium`. Top driver found by
  summing NILM event kWh per appliance. *Evidence:* cost engine + power-source
  attribution of the driver.

- **#8 `comparative_regression`** — *Fires when:* for any appliance,
  `this_week_kwh ÷ same_week_last_month_kwh` **≥ 1.20**. *Severity:* `medium`.
  *Evidence:* power-source week-vs-week delta + routine engine (conditions similar).

- **#9 `routine_shift`** — *Fires when:* any K-Means phase boundary drifts
  **≥ 60 min** vs last month. *Severity:* `low`.
  *Evidence:* K-Means drift + routine engine (schedules may lag).

**Family D — Context**

- **#10 `weather_correlated_ac`** — *Fires when:* **≥ 1** forecast day **> 33 °C**
  in next 7 AND learned hot-day AC uplift **≥ 25 %**. *Severity:* `low`.
  *Evidence:* Open-Meteo forecast + routine engine (learned uplift).

- **#11 `anomaly_with_action`** — *Fires when:* Isolation Forest score **< −0.1**
  AND the event is an *actionable appliance at an off-hour* (water_heater/iron/
  kettle running 00:00–~05:00). *Severity:* `medium`.
  *Evidence:* Isolation Forest score + routine engine (normally inactive then).
  *Note:* gated to known fixes so it never says "broken," only "check this."

**Family E — Capital**

- **#12 `inefficient_upgrade`** — *Fires when:* a steady-state load draws
  **> 1.3 ×** its efficient-class average (from the ST registry). *Severity:* `low`.
  *Evidence:* NILM steady-state draw + ST efficiency registry 5-star average.
  *Note:* says "inefficient **by design**," not "faulty" — no health model needed.

> Reading these aloud is your strongest Q&A move: every card is a short,
> inspectable rule over typed facts — not a black box. "Show me why card #5
> appeared" → "projected 1,520 kWh, cliff at 1,500, RP4 step from 27 to 37 sen."

---

## Stage 3 — QUANTIFY: ringgit + effort

`quantifier.py`. Turns a Situation into auditable numbers:
```
wasted_kwh = watts × duration / 1000
wasted_RM  = wasted_kwh × TNB_RP4_marginal_rate(timestamp)   ← tnb_tariff
monthly_RM = wasted_RM × frequency_per_month                  ← routine history
confidence = combined input confidences;  effort = low/med/high
```
Every numeric claim on a card traces to `raw_metrics` + a tariff call.

## Stage 4 — TEMPLATE: the words
`templates.py`. Deterministic per-(situation) text — judges can verify nothing is
hallucinated. **An LLM (Gemini) is used only for optional narrative polish, never
for numbers or on the load-bearing path.**

## Stage 5 — RANK: what surfaces
`ranker.py`. Roughly `score ≈ impact_RM × confidence × novelty × severity`,
**suppressed by recent dismissals**. Top 2 surfaced, rest secondary.

## Stage 6 — LEARN: close the loop
User acts (WhatsApp reply *or* in-app tap) → both write `_user_actions.json` →
`feedback_loader.py` feeds `dismissed_archetypes` + `recently_shown` back into the
ranker (7-day dismiss decay, 3-day novelty cooldown). **The returning arrow is what
makes it a loop, not a pipeline** — and lets you honestly say "it learns from
rejection."

---

## Worked example (the one to walk on the slide + demo live)

```
1. DETECT   NILM/AC clamp: AC = 1200 W. Occupancy: away since 14:19.
            K-Means: phase = work. Routine: AC usually off in work phase.
2. COMPOSE  All four agree → Situation left_on_empty, severity high.
3. QUANTIFY 71 min × 1200 W = 1.42 kWh × peak RP4 rate ≈ RM0.57 now;
            × ~4×/week ≈ RM9–10/month.
4. TEMPLATE "AC ran 71 min after the room emptied at 14:19 … ~RM10/month.
            Enable auto-off after 20 min empty."
5. RANK     High impact + high confidence → surfaced as top card.
6. LEARN    WhatsApp alert → reply Y → ESP32 IR + relay → AC clamp confirms 0 W →
            confirmation back. Dismiss/accept re-ranks future cards.
```

This is the **only** card that can fire from minutes of live data (instant
signals) — which is exactly why it's the live hero moment.

---

## Honest caveats (have these ready)

- **Live ≠ breadth.** Most archetypes need *history* (month of kWh, learned
  baselines, anomaly model). From minutes of live feed only `left_on_empty`
  (and maybe `simultaneous_peak_load`) can fire. Breadth is proven by **replaying
  a recorded week** through the same engine — not by live.
- **Three data states:** *Showcase* (hand-built snapshot, trips all archetypes) ·
  *Replay* (recorded/synthetic or your bench log) · *Live* (Pi feed now). The
  app tags each card `LIVE` / `REPLAY` / `SHOWCASE` — it never calls synthetic
  data live.
- **NILM identifies appliance *class*, not unit count**; the signature library
  labels distinctive isolated loads, not a tangled always-on cluster.
- **AC is measured, not inferred** (dedicated clamp); for low-PF loads the live
  number is apparent power until calibrated.

## Pitch lines
- *"Many cheap typed signals in — measured, learned, contextual. The correlator
  composes them into one evidenced claim. The intelligence is the composition,
  not the model count."*
- *"Every number on a card traces to a tariff call and its raw metrics — you can
  audit it line by line. No LLM touches the numbers."*
- *"The off-switch is the easy part; knowing it's worth doing *now*, pricing it,
  and proving it worked — that's the loop."*

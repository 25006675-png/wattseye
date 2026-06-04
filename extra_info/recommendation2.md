# Fixing the WhatsApp-only assumption (it's actually a strength, not a break)

The current "You — WhatsApp reply" node makes it look like every card pushes a notification. From your `whatsapp.py` the truth is much better: only 4 of 12 archetypes push to WhatsApp (`left_on_empty`, `rp4_tier_cliff`, `anomaly_with_action`, `bill_trending_high`). The other 8 live in the app's Coach tab waiting for the user.

Reframe it as a feature, not a footnote. One label swap and one verbal line do it:

- Slide node label: `"You decide — in app or WhatsApp"`
- Subtitle add: `"Urgent cards interrupt you on WhatsApp; the rest wait in the app."`
- Spoken line:
  > "We're not a spam system. Only 4 of 12 card types are urgent enough to push to your WhatsApp — empty-room AC, tier-cliff warning, anomaly, bill drift. The other 8 sit in the app's Coach tab for when you have a moment. Either channel, the same reply feeds the same learning loop."

That's it. The loop doesn't break — both channels write to the same `_user_actions.json` that the `feedback_loader` reads. Make sure the in-app dismiss/accept buttons actually POST to the same log (if they don't yet, that's the same ~30-min fix as the WhatsApp side; the webhook handler can be reused).

## Why this strengthens the story

- Restraint = product maturity. Most demos over-notify.
- It gives you a defensible answer to "won't users get spammed?" — judges always ask.
- It introduces the app naturally, without making the WhatsApp loop look incomplete.

So the loop slide stays. The companion slide (software logic + 12 cards) is where you'd show which archetypes go which channel — see the Channel column in the table below.

# What each model analyses (one line each)

| Model | What it asks |
|---|---|
| NILM (ELECTRIcity Transformer) | Which appliance is using how much power right now? — disaggregation on the main clamp residual |
| Isolation Forest | Is this event statistically unusual vs the home's own history? |
| Linear Regression | Is this appliance drifting from its own healthy baseline? (fridge duty cycle) |
| K-Means | Which daily phase is the home in? — morning / work / evening / sleep |
| Routine baseline (statistical, not ML) | Is this behaviour normal for this home at this hour? |
| TNB RP4 tariff (deterministic math) | What does this cost in real ringgit, at the marginal rate? |
| Weather (Open-Meteo) | Is a hot day coming that will push AC use up? |

# 12 cards × rules × models (compact table)

| # | Card | Family | Channel | Rule (shortened) | Models / signals used |
|---|---|---|---|---|---|
| 1 | `left_on_empty` | Waste | WA + app | NILM appliance ≥ threshold W for ≥ 30 min AND Occupancy=away ≥ 20 min AND phase≠sleep | NILM + Occupancy + K-Means + Routine |
| 2 | `phantom_standby` | Waste | App | Overnight min-window baseline > 30 W for 3+ nights | NILM minimum-window |
| 3 | `simultaneous_peak_load` | Waste | App | ≥ 2 heavy appliances concurrent inside ToU peak (14–22 weekdays) | NILM concurrency + tariff windows |
| 4 | `tou_switch` | Tariff | App | off_peak_kWh / total_kWh ≥ 60% over 30 d AND ToU saves ≥ RM 5/mo | Routine totals + TNB ToU vs standard |
| 5 | `rp4_tier_cliff` | Tariff | WA + app | projected_monthly_kWh within ±50 of 1500 AND day_of_month ≥ 15 | Forecast kWh + TNB RP4 cliff |
| 6 | `peak_window_shift` | Tariff | App | Scheduling-friendly appliance (dishwasher/washer) ran in peak ≥ 2× in last 7 d | NILM event log + tariff windows |
| 7 | `bill_trending_high` | Forecast | WA + app | projected_kWh ≥ last_3mo_avg × 1.15 AND ≥ 1 driver appliance identified | NILM attribution + 3-month baseline |
| 8 | `comparative_regression` | Forecast | App | This week vs same-week-last-month ≥ +25% for a single appliance | NILM + week baseline diff |
| 9 | `routine_shift` | Forecast | App | A K-Means phase boundary drifted ≥ 60 min over 3 weeks | K-Means phase drift |
| 10 | `weather_correlated_ac` | Context | App | hot_days_next_7 ≥ 2 AND historical hot-day AC uplift ≥ 30% | NILM + Open-Meteo + correlation |
| 11 | `anomaly_with_action` | Context | WA + app | Isolation Forest score < −0.3 AND event maps to a known fix template | Isolation Forest + actionable lookup |
| 12 | `inefficient_upgrade` | Capital | App | Steady-state load > 1.3 × MEPS class average for its size band | NILM steady-state + ST efficiency registry |

# Two patterns worth saying aloud on the companion slide

1. "Almost every card joins NILM with one other signal — the rules are mostly two-model joins, not 12 unique algorithms."

   That makes the system sound coherent rather than sprawling.

2. "The Channel column is the restraint dial — only 4 cards earn an interruption."

   Ties back to the app-vs-WhatsApp framing above.


    IF   NILM says AC ≥ 800W for 30+ min        (ML signal 1)
  AND  Occupancy says room empty 20+ min      (ML signal 2)
  AND  K-Means says this is "work phase"      (ML signal 3)
  AND  Routine baseline says AC unusual now   (ML signal 4)
  →    Situation: AC running in empty room
       RM impact = wasted_kWh × TNB marginal rate

  That's the shape. Judges now know what a rule looks like in your system.

  Layer 2: The taxonomy of the other 11 (10 sec, one slide). Five families, one line each:

  WASTE     (3 rules) — empty room · phantom standby · peak overlap
  TARIFF    (3 rules) — ToU switch · RP4 cliff · peak-window shift
  FORECAST  (3 rules) — bill trending · week vs last · routine drift
  CONTEXT   (2 rules) — hot day · actionable anomaly
  CAPITAL   (1 rule)  — inefficient upgrade

  Layer 3: One sentence that closes it (5 sec). "Same shape on all 12: ML signals join into a named situation, the tariff engine puts
  ringgit on it, the template writes it, the ranker decides what surfaces. If you've seen one, you've seen the system."
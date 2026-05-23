• You’re right to reset the thinking first. Looking broadly at real recommendation products, the strongest ones usually don’t win because
  they “recommend things.” They win because they make recommendations feel timely, explainable, low-effort, and measurable.

  What Strong Products Do

  1. They explain why
     Good recommendation UX shows the reason, not just the output.

     Example pattern:

     Recommended because:
     - You often do X at this time
     - Your recent behavior changed
     - This option matches your goal

     This appears in explainable AI recommendation work, where trust improves when users can understand why something was suggested. Sourc
     e: https://kalyan-talari.designfolio.me/project/68ff2ef2cb2d80278cc45892

  2. They recommend actions, not information
     The better examples don’t stop at “insight.” They push toward a next step.

     MyBehavior, a health behavior app, used personal logs to suggest small behavior changes. Users rated personalized suggestions more po
     sitively than generic expert suggestions. Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC4812832/
  3. They match timing to context
     A healthcare recommendation study found timing matters: the app open time and content theme matching influenced behavior. Source:
     https://journals.sagepub.com/doi/abs/10.3233/ATDE230592

     In simple terms: the best recommendation is not only “what,” but “when.”
  4. They create a feedback loop
     Professional systems improve through user behavior: clicks, purchases, completion, dismissals, saves, or repeated engagement.

     Retail recommendation case studies often use browsing, cart, purchase, and click signals to improve recommendations. Source:
     https://www.clearscale.com/case-studies/fiftyflowers-case-study
  5. They measure outcome
     Strong products prove recommendation quality using metrics:

     conversion lift
     engagement increase
     completion rate
     retention
     action taken
     savings achieved

     Example: Coach/Jewel ML reports A/B-tested revenue uplift from personalized product discovery. Source:
     https://www.jewelml.com/customer-stories/coach

  Winning Design Direction
  The best mentor advice: don’t design a “recommendation list.” Design a decision loop.

  Detect -> Explain -> Recommend -> Help act -> Learn -> Prove impact

  That is much stronger than:

  Show user several tips

  A Professional Recommendation Card
  Use this mental model:

  1. What happened?
  2. Why does it matter?
  3. Why are we recommending this?
  4. What should the user do now?
  5. How easy is it?
  6. What result can they expect?
  7. Did it work?

  Visual example:

  Recommended Action

  You can reduce repeat waste this week.

  Why this appeared:
  Your recent pattern changed from your normal routine.

  Best next step:
  Try this small action for 3 days.

  Expected impact:
  Medium saving / low effort

  Actions:
  [Do now] [Remind me] [Not useful]

  What Feels Innovative
  The innovation is not “AI recommends.” Everyone says that now.

  The innovation is:

  Recommendation with proof
  Recommendation with explanation
  Recommendation with timing
  Recommendation with user control
  Recommendation that learns from rejection
  Recommendation that closes the loop after action

  Judge-Friendly Framing
  Say this:

  > “Our recommendation system is not a generic tips feed. It is an explainable action engine. It ranks suggestions by personal relevance,
  > timing, confidence, effort, and measurable impact.”

  That sounds much more professional than:

  > “We use AI to recommend things.”

  Core Principle To Steal
  From professional examples, the pattern is clear:

  Personal data alone is not enough.
  A good recommendation needs:
  context + explanation + action + feedback + measurable result.

  That is the direction I would use if the goal is to win.



  Below is how it should work conceptually, in five layers. Rules alone can't do it — but pure ML can't either. It's a pipeline.

  Layer 1: Models produce typed detections, not insights

  Each model already does one narrow job. Keep them narrow. They emit structured records, not sentences:

  NILM           → AppliancePowerEstimate(appliance=kettle, watts=2050, t=07:14:22, confidence=0.91)
  K-Means        → PhaseLabel(phase="morning", t=07:14, distance_to_centroid=0.23)
  Isolation F.   → AnomalyScore(event_id=…, score=-0.42, features={peak_W, dur, hour, phase})
  LR fridge      → HealthResidual(appliance=fridge, expected_duty=0.31, actual_duty=0.44, z=2.1)
  Routine engine → DeviationFact(metric="ac_off_hours_after_leave", baseline=12min, actual=71min)
  Occupancy      → OccupancyState(state="away", since=14:02, confidence=0.88)
  Cost engine    → ProjectedBill(month_kwh=312, RM=148.20, vs_last=+22%)

  These are facts with confidence, not prose. This is the layer your ML produces today.

  Layer 2: A correlator joins detections into situations

  This is the missing piece in most projects. One detection alone is rarely actionable. Joined detections are.

  Examples of join rules (deterministic — this part is rules, and that's fine):

  IF  OccupancyState = away
  AND NILM.AC.watts > 800 for ≥ 30 min
  AND PhaseLabel = work
  THEN  Situation = "AC running while empty during work phase"
        Severity = high
        Evidence = [the three detections above with their timestamps]

  IF  HealthResidual(fridge).z > 2 for ≥ 3 consecutive days
  AND DeviationFact(fridge.daily_kwh) > baseline + 15%
  THEN  Situation = "Fridge running harder than usual for multiple days"
        Severity = medium

  The correlator's job is to detect a named situation — not to write the card text yet. Think of it as an expert system layer that sits on
  top of the ML, asking "do I have enough independent evidence to claim something specific?"

  Why this isn't "just rules": the inputs are ML-derived (NILM appliance ID, IF anomaly score, K-Means phase, LR residual). Rules without
  ML would have nothing useful to join. ML without rules would have no clear claim to make. The correlator is where they meet.

  Layer 3: A quantifier attaches RM and effort to every situation

  Once a situation is named, compute the numbers a card needs:

  For "AC running while empty":
    wasted_kwh   = (NILM.AC.watts × duration) / 1000
    wasted_RM    = wasted_kwh × tariff_at(timestamp)  ← uses tnb_tariff.py
    monthly_RM   = wasted_RM × frequency_per_month     ← uses routine history
    effort       = "low"   (set auto-off, no purchase)
    confidence   = min(NILM.conf, Occupancy.conf, K-Means.conf)

  For "Fridge unhealthy":
  extra_kwh    = (actual_duty − expected_duty) × 24 × fridge_power_W / 1000
  monthly_RM   = extra_kwh × 30 × tariff
  effort       = "medium"  (clean coils → DIY; replace seal → service call)
  confidence   = LR.confidence × HealthResidual.z_normalised

  Now the card has the four things your recommendation.md design demands: what happened, why, expected impact, effort.

  Layer 4: A template turns the situation + numbers into sentences

  Templates are appliance-and-situation-specific, not generic. One template per (situation, appliance) pair:

  Template: ac_running_empty
  "Your {appliance} ran {duration_min} min after the room was empty at {time}.
   That's about {wasted_RM} per occurrence, or {monthly_RM}/month at this frequency.
   Try: {action_specific_to_appliance}.
   Expected saving: {monthly_RM}/month. Effort: {effort}."

  Template: fridge_health_drift
  "Your fridge's compressor is cycling {extra_pct}% more than usual this week.
   Likely causes: dirty condenser coil, weak door seal, or higher room temperature.
   Suggested check: clean coils (15 min, free) or call service if persistent.
   If unaddressed, estimated extra: {monthly_RM}/month."

  Templates are mechanical text — not an LLM. Judges can read them and verify nothing is hallucinated. This is the right call for a
  hackathon. (You could swap an LLM in later; the structure stays the same.)

  Layer 5: A ranker decides what surfaces in which tab

  You have two tabs (Routine + Recommendation) — they should pull from the same pool but filter differently.

  score = impact_RM × confidence × novelty × (1 − recent_dismiss_decay)

  Where:
    impact_RM   = monthly_RM from layer 3
    confidence  = joint confidence from layer 3
    novelty     = 1 if not shown in past 7 days, decays otherwise
    dismiss_decay = if user dismissed similar card recently, suppress

  Routine tab          → show situations of type {pattern, phase, baseline_deviation}
  Recommendation tab   → show situations of type {actionable_savings, health, capital}
                         ranked by score, max 2 active cards

  That ranker is the thing that lets you honestly say "it learns from rejection" — dismissals modify the score for similar future cards.
  Even a simple counter is enough to claim it.

  How the two tabs differ

  This is the part your mock UI is hand-waving:

  - Routine tab = "here is what your home normally does, and what was different today." It's descriptive. Phase timeline, baseline vs
  today, "AC usually starts at 8 PM but started at 6 PM today." No action required — it's the understanding surface.
  - Recommendation tab = "here are 1–2 specific things to do, ranked by RM impact." It's prescriptive. Each card is a situation that passed
   Layer 2's correlator with severity ≥ medium and has a concrete action in Layer 4's template.

  Same data pipeline, different filter on Layer 5. A pattern shown in Routine becomes a Recommendation only when (a) correlator names a
  situation, (b) quantifier finds material RM, and (c) template has a concrete action.

  End-to-end example, concretely

  Take "AC running in empty room":

  1. Models fire: NILM sees 1200W on AC circuit. Occupancy says "away since 14:02." K-Means says phase = work. Routine engine says "AC is
  usually off during work phase, last 14 days."
  2. Correlator joins: all four agree → Situation ac_running_empty triggered, severity = high (>30 min + >1000W + work phase).
  3. Quantifier: 71 min × 1200W = 1.42 kWh × RM 0.40 (peak ToU) = RM 0.57 wasted today. Routine frequency = 4 days/week → ~RM 9.80/month.
  4. Template: fills ac_running_empty template with those numbers + action "Enable AC auto-off after 20 min empty."
  5. Ranker: score = 9.80 × 0.85 × 1.0 × 1.0 = 8.33. High enough to surface. Not dismissed before. Shows as top card in Recommendation tab.
   Routine tab shows the same event as a deviation marker on the daily timeline.

  That's the full path. Each layer is small, testable, and replaceable. No layer needs to be "smart" on its own — the intelligence is in
  the chained composition.

  Honest summary

  - Your models are sufficient. Don't add more.
  - What you're missing is Layers 2 + 4 + 5 — the correlator, the templates, and the ranker. Layer 3 (quantifier) is partly in
  cost_engine.py already.
  - This is not "rules vs ML." It's ML for detection, rules for composition, math for quantification, templates for language, ranker for
  prioritisation. Each layer plays to its strength.
  - For the pitch: "Our models detect; our orchestrator composes; our tariff engine quantifies; our ranker decides what surfaces. The user
  sees one card. Behind it are four models and a deterministic chain that you can audit line-by-line." That a




   The action-oriented set (12 archetypes)

  Family A — Waste detection (behavioural, immediate action)

  1. Appliance-left-on-while-empty
  Action: "AC ran 71 min after you left at 2:02 PM. Enable auto-off after 20 min empty. Est. RM 9/month."
  Linked ML: NILM + Occupancy + Routine baseline.

  2. Phantom / standby load
  Action: "Your home draws 48W overnight from standby devices — about RM 6/month. Top contributors: TV cluster, router. Unplug or use a
  smart switch."
  Linked ML: NILM minimum-window baseline.

  3. Simultaneous heavy load during peak window
  Action: "Kettle, microwave, and AC all ran together at 7:34 PM (peak). Staggering kettle/microwave to off-peak saves ~RM 4/month."
  Linked ML: NILM concurrency + ToU window.

  Family B — Tariff optimisation (uniquely Malaysian)

  4. ToU tariff switch recommendation
  Action: "65% of your usage is off-peak. Switching to TNB ToU could save ~RM 12/month based on last 30 days."
  Linked ML: Routine engine + tnb_tariff.py ToU vs standard comparison.

  5. RP4 tier cliff warning (1500 kWh)
  Action: "You're projected to hit 1,520 kWh. Crossing 1,500 raises generation rate by 10 sen/kWh on every unit above. Cutting 25 kWh keeps
   you in the lower tier — saves ~RM 18 this month."
  Linked ML: tnb_tariff.py + projected kWh.

  6. Peak-window load shift
  Action: "Your dishwasher and washer typically run 7–9 PM (peak). Shifting to after 10 PM saves ~RM 6/month on ToU."
  Linked ML: NILM + scheduling-friendly appliance signatures + ToU windows.

  Family C — Forecast & trend (anticipatory)

  7. Bill trending high mid-cycle
  Action: "You're on track for RM 168 this month, +22% vs your usual RM 138. Main driver: AC use 2–5 PM increased. Raise setpoint by 1°C to
   save ~RM 8 over remaining days."
  Linked ML: Cost engine + NILM attribution.

  8. Comparative-period regression (week-vs-week, month-vs-month)
  Action: "Your AC used 38% more energy this week vs last month's same week. Try +1°C setpoint — expected saving ~RM 11/month."
  Linked ML: NILM + routine baseline diff.

  9. Routine-shift drift
  Action: "Your evening phase has shifted ~90 min later over the last 3 weeks. Your AC schedule still assumes the old timing — adjust by ~1
   hour to save ~RM 7/month."
  Linked ML: K-Means phase boundary drift.

  Family D — Context-aware (external signals)

  10. Weather-correlated load increase
  Action: "Hot days (>33°C) push your AC usage up 45%. Pre-cool 30 min before peak window starts on forecasted hot days next week — saves
  ~RM 9 for the week."
  Linked ML: NILM + weather API + ToU window.

  11. Anomaly with suggested check (only when actionable)
  Action: "Water heater ran at 2:14 AM — unusual for your home. If unintended, check the timer setting; otherwise dismiss. Continued
  unattended overnight usage ~RM 14/month."
  Linked ML: Isolation Forest with action template only when anomaly maps to a known fix.

  Family E — Capital decisions (longer-term, government-data-backed)

  12. Inefficient continuous load → upgrade comparison
  Action: "Your fridge draws 180W idle. 5-star models this size average 90W. Estimated saving: RM 240/year. Payback on RM 1,800
  replacement: ~7.5 years. [See 5-star models on ST registry]"
  Linked ML: NILM steady-state estimate + ST efficiency registry lookup.

  (Note: this archetype uses NILM's idle-power reading, not health drift. It says "your appliance is inefficient by design" — not "your
  appliance is broken". That distinction is what keeps it defensible without needing the LR health model.)

  Demo set (5–6 cards to actually wire up)

  Strongly recommend: 1, 2, 4, 5, 7, 12.

  - 1 + 2 = visceral, easy to demo physically.
  - 4 + 5 = the uniquely-Malaysian RP4 plays. These are the cards judges will remember because no foreign product can produce them.
  - 7 = ties everything to the bill — the user's actual concern.
  - 12 = the capital/government-registry play, which is your "credibility, not commerce" moment.

  That's 6 cards spanning 4 of the 5 families. Plenty to populate a demo that looks like a system without overpromising.

  What about Family C #9 (routine-shift drift)?

  Worth wiring up if and only if your K-Means already shows visible phase boundaries on the synthetic data. If yes, include it — it's the
  one card that visibly uses the clustering model in the UI. If the phases aren't crisp enough to demo, drop it.

  Slide framing for the pitch

  Don't list all 12. Say:

  ▎ "WattsEye produces five families of recommendations: waste detection, tariff optimisation, forecast & trend, context-aware, and capital
  ▎  decisions. Today we'll show six representative cards across four of these families. The full taxonomy is in our roadmap."

  Five families × representative demo = looks deliberate. Twelve flat items = looks like a feature list. Same content, different
  impression.

  Net summary

  - Dropped health drift (no data) and new-appliance (dashboard event, not advice). Correct calls.
  - Down to 12 action-bearing archetypes organised into 5 families.
  - Demo 6 cards: #1, 2, 4, 5, 7, 12 — covers behavioural, tariff, forecast, and capital, with the two strongest uniquely-Malaysian plays
  (4 and 5) front and centre.
  - Keep the other 6 archetypes on a roadmap slide so the surface area looks intentional, not absent.
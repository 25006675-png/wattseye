 You're right — in a room where every team shipped something that runs, "it works" is the floor, not the ceiling. AI
  coding tools collapsed the value of building. What they did not commoditize is truth, ownership, and stakes: whether your
  claims are real, whether the advantage is yours, and whether it matters. That's where you win or lose now. Here's how
  I'd play WattsEye to the top.

  1. Bet the whole demo on the three things a prompt can't produce

  Everything in your repo that an AI could regenerate in an afternoon is table stakes — the Flutter app, the coach
  templates, the dashboard. Stop spending demo time on those. Spend it on your three unfair advantages:

  - Physical hardware that does something irreversible on stage. The mmWave → WhatsApp → IR → relay → clamp reads 0 W loop
  is the single most defensible 30 seconds you have. No team with a laptop and Cursor can fake a hair dryer audibly cutting
  off. This is your spine. If anything gets polished to perfection this week, it's this loop — rehearsed until it's boring
  to you.
  - Reproducible proof. We just established something almost no team can claim: your headline numbers are byte-for-byte
  verifiable (verify_f1.py reproduces 0.96/0.86/0.80/0.76/0.68 from the real weights). Most ML demos are unfalsifiable.
  Make verifiability visible: "Every number on this screen traces to code you can run — here, watch me recompute our
  accuracy live." In a sea of trust-us AI demos, being the team that can be checked is a flex.
  - The Malaysian moat. TNB RP4, the 1,500 kWh cliff, ToU break-even, EEI rebate, Bahasa, WhatsApp-native.
  Sense/Emporia/Sensibo cannot produce these, and a generic prompt won't either without your local knowledge. This is
  genuine domain ownership.

  If a feature isn't one of these three, it's supporting cast.

  2. Get ONE real home running. This is the highest-leverage move left.

  Your roadmap has a single-home pilot 30 May–5 Jun. Do it, even crudely, and harvest one real human story: "This family's
  fridge was quietly costing them RM X/month — here's the actual WhatsApp thread, here's what they changed." A real
  anecdote with a real person and real ringgit detonates harder than any architecture diagram or synthetic 12-card wall. AI
  can fabricate a polished demo; it cannot fabricate a true user. Right now your dashboard is admittedly driven by
  _demo_snapshot() — "a synthetic snapshot that triggers most archetypes." One genuine finding from one real week is worth
  more than all twelve.

  3. Make your demo show the system being wrong — and recovering

  Happy-path demos read as rehearsed and slightly fake to experienced judges. The senior move: deliberately show a
  limitation and how the architecture absorbs it. "Watch — NILM mislabels this load… but the dedicated AC clamp catches it
  directly, and anything we can't classify yet still shows up in the measured unknown bucket. We never lose a watt; we just
  label more over time." Showing the failure mode and the graceful handling demonstrates engineering maturity that no
  competitor showing only green checkmarks can match.

  And do one live counterfactual: run your ToU comparator on a real 30-day profile on stage and answer the question every
  TNB customer has and can't answer — "should I switch?" Plus the 1,500 kWh cliff alert as a 10-second "wait, I didn't know
  that costs me 10 sen extra on every unit" moment. Those two are uniquely yours and uniquely Malaysian.

  4. Lead with the data flywheel — it's your only compounding moat

  A working prototype is a snapshot; judges fund trajectories. Your real defensibility is the auto-labeling loop you
  already designed: every second you log (main-feeder window, dedicated-AC reading) → free, perfectly-labeled training data
  with zero user effort. Say it plainly: "Every WattsEye home makes the next home's model better, with no manual labeling.
  A smart-plug company can never build that dataset. That's the moat — not the transformer." This reframes you from "a
  gadget" to "a data network that gets smarter," which is the difference between a hackathon project and a company.

  5. Subtract aggressively — taste is the new scarcity

  When features are cheap to generate, restraint signals judgment. Your own recommendation.md already nailed this ("show 6
  cards across 4 families, not 12 flat; we dropped health-drift because no dataset supports it"). That decision log — what
  you chose not to build, and why — is more impressive than volume, because it proves you can tell signal from noise. Put
  one slide of "things we deliberately cut and the reason." Almost no team does this; it reads as senior every time.

  Concretely: don't pitch "we use AI/ML." Everyone does. Pitch the composition — "four narrow models emit typed facts; a
  deterministic correlator joins them into named situations; a tariff engine quantifies the ringgit; a ranker decides what
  surfaces and learns from dismissals. The intelligence is in the chain, and you can audit it line by line." The systems
  thinking is the differentiator; the model is a commodity.

  6. Kill the claims that can unravel you

  A single number a judge can poke and break takes the whole pitch's credibility with it. Right now your exposure:

  - "Direct measurement" for AC. Your own QA doc admits it's apparent power (VA), and inverter AC — the hero load — is
  exactly where PF error is worst (10–40%). Say "direct current measurement on the AC branch" and show the PZEM/ADE7953
  upgrade path. Don't let "direct = exact watts" stand naked.
  - The impact slide (RM 90M, 35,000 tonnes, ~7,500 cars). Either show the one-line model behind it or soften it.
  Unsupported big numbers invite a skeptic to start pulling threads.
  - Absolutes ("Malaysia's first," "nobody measures AC"). One informed judge with a counterexample ends it. "To our
  knowledge, no consumer product models the TNB bill the way we do" is unbreakable and still strong.

  The counterintuitive truth: in a field of overclaiming AI demos, calibrated honesty is a competitive weapon. The team
  that volunteers its error bars and says exactly what's live vs replay reads as the one that actually understands its
  system.

  ---
  The one-sentence version: when code is free, win on the things code can't buy — a physical loop that fires live, claims a
  judge can reproduce on the spot, a real home with a real saving, and a data flywheel that compounds. Build the demo
  around what can't be prompted into existence, and cut everything that can.

  Want me to turn this into a concrete demo run-of-show (minute-by-minute, with the failure-and-recovery beat and the live
  ToU/cliff moments scripted), or a tightened pitch-slide outline?
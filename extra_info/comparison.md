You're spot-on to flag this. Let me be honest about what's old and what's actually new.

  Remote appliance control: not novel, mature category

  Things that have existed for 5–10 years already:

  | Product | Year | Does what |
  |---|---|---|
  | Smart plugs (TP-Link Kasa, Wemo) | 2014+ | Remote on/off per plugged device |
  | WiFi-native ACs (Daikin, Mitsubishi apps) | 2015+ | Direct AC control |
  | Sensibo, Cielo, Mitsuhome | 2015+ | IR blaster + AC scheduling via app |
  | Google Home / Alexa | 2016+ | Voice control of any connected device |
  | Geofencing ("turn off AC when last person leaves") | 2017+ | Location-triggered automation |

  If WattsEye's pitch is "we can turn your AC off remotely" — yes, a judge SHOULD push back. That's a $30 Sensibo product.

  So what's actually new about WattsEye

  The control mechanism isn't the moat. The decision logic that drives the control is. Specifically:

  | Step in WattsEye flow | Smart plug / Sensibo equivalent |
  |---|---|
  | 1. Detect AC is running (dedicated CT clamp at the DB box) | Smart plug only sees plug load, not hardwired AC |
  | 2. Detect room is empty (mmWave sensor) | Sensibo doesn't measure occupancy |
  | 3. Compare against learned home routine ("this is unusual for your weekday afternoon") | Generic schedulers don't learn per-home patterns |
  | 4. Compute avoidable cost at current TNB band (RM 0.32/kWh × duration) | Apps use flat-rate estimates if any |
  | 5. Confirm with user via WhatsApp | Sensibo silently executes scheduled rules |
  | 6. Execute IR cutoff | This is the commodity step |
  | 7. Verify power dropped to 0W via the same CT clamp | Sensibo just hopes it worked |
  | 8. Log the saving and credit it on the dashboard | None |

  Smart plugs and Sensibo do steps 6 and 7-ish only. WattsEye does steps 1–8. Control is the last step of an 8-step
  decision loop.

  The honest competitive positioning

  This is roughly how WattsEye stacks up against existing products:

  | Product | NILM | Dedicated AC clamp | Occupancy sensor | Routine learning | TNB-accurate billing | IR/control | Closed-loop verify |
  |---|---|---|---|---|---|---|---|
  | Smart plug (Kasa) | — | — | — | — | — | per plug | — |
  | Sensibo | — | — | — | — | — | ✅ | — |
  | WiFi AC app | — | — | — | basic | — | ✅ | — |
  | Sense / Emporia | ✅ | — | — | — | rough | — | — |
  | Google Nest Hub | — | — | partial | ✅ | — | via plugins | — |
  | **WattsEye** | ✅ | ✅ | ✅ | ✅ | ✅ (RP4 + ToU) | ✅ | ✅ |

  Nobody combines all of these — particularly not for the Malaysian market with TNB RP4 accuracy and the inverter-AC
  dedicated clamp.

  The pitch reframe

  Wrong way (what you might be doing):
  "WattsEye can turn off your AC when nobody's in the room."
  → Judge: "Sensibo does that for RM 250."

  Right way:
  "WattsEye knows what every watt in your home is doing. When AC is running in an empty room, that's just one of many
  things we can detect. The control is downstream — the moat is the sensing, classification, and decision logic that knows
  when to act. Smart plugs only see what's plugged in. Sensibo only sees the AC. WattsEye sees the whole bill."

  The closed-loop verify (step 7 above) is also a small but real differentiator. Most products fire and forget. WattsEye
  confirms.

  My honest judge take

  If you frame WattsEye as a remote-control product, you lose. There are mature commercial alternatives.

  If you frame WattsEye as an integrated sensing + classification + decision + control + verification system where each
  layer informs the next, you win — because that integration genuinely doesn't exist at the consumer level for Malaysian
  homes.

  The IR cutoff is theater for the demo, not the product. It's the visible moment that proves the invisible decision system
   works. Don't pitch the IR. Pitch the eight-step loop, and let the IR cutoff be the satisfying punchline.

  One concrete suggestion
  "WattsEye can turn off your AC when nobody's in the room."
  → Judge: "Sensibo does that for RM 250."

  Right way:
  "WattsEye knows what every watt in your home is doing. When AC is running in an empty room, that's just one of many
  things we can detect. The control is downstream — the moat is the sensing, classification, and decision logic that knows
  when to act. Smart plugs only see what's plugged in. Sensibo only sees the AC. WattsEye sees the whole bill."

  The closed-loop verify (step 7 above) is also a small but real differentiator. Most products fire and forget. WattsEye
  confirms.

  My honest judge take

  If you frame WattsEye as a remote-control product, you lose. There are mature commercial alternatives.

  If you frame WattsEye as an integrated sensing + classification + decision + control + verification system where each
  layer informs the next, you win — because that integration genuinely doesn't exist at the consumer level for Malaysian
  homes.

  The IR cutoff is theater for the demo, not the product. It's the visible moment that proves the invisible decision system
   works. Don't pitch the IR. Pitch the eight-step loop, and let the IR cutoff be the satisfying punchline.

  One concrete suggestion

  Add a slide titled "Competitive Landscape" with the table above. Most teams skip this slide because they think it draws
  attention to competitors. It does the opposite for you — it forces the judge's eye to the ✅ column for WattsEye, which
  is the only product that has every column checked.

  This converts the "haven't I seen this before?" worry into "oh, I see what makes this different."

  Want me to draft that slide as a markdown table you can hand to whoever does slides?




  Sense (US, ~USD 300 hardware)

  - Per-appliance monitoring: Yes, via pure NILM from one main clamp. They market "device detection" — fridge, microwave, EV charger, AC,
  etc. Famously slow to detect (weeks to months per device) and inverter ACs are a known weak spot they don't advertise.
  - Bill predictor: Yes — monthly bill projection, "you're on track to spend $X."
  - Recommendations: Light. Mostly anomaly alerts ("device left on", "always-on costing you $X/month"), some time-of-use guidance in
  supported utilities.
  - Gap vs you: US tariffs only. No tiered/AFA modelling. Pure NILM struggles with inverter AC.

  Emporia Vue (US, ~USD 150 hardware)

  - Per-appliance monitoring: Yes, but per-circuit, not NILM. You install 8 or 16 individual CT clamps on circuit-breaker branches. So
  "appliances" really means "circuits."
  - Bill predictor: Yes, basic.
  - Recommendations: Minimal. It's more of a power-user monitoring product than an advisory product.
  - Gap vs you: Requires opening the breaker panel and installing many clamps. No ML insight layer.

  Bidgely (B2B, sold to utilities)

  - Per-appliance monitoring: Yes, NILM-based — they license it to utilities like Singapore Power, ENGIE, E.ON. End-users see it inside
  their utility's app.
  - Bill predictor: Yes, very strong.
  - Recommendations: Strong — they brand it "UtilityAI" and ship personalised tips through utility apps.
  - Gap vs you: Not consumer-purchasable. You can't buy Bidgely. A Malaysian consumer has no path to it unless TNB licenses it (they
  haven't).

  Octopus Energy (UK, utility-bundled)

  - Per-appliance monitoring: No, mostly whole-home + smart-meter data.
  - Bill predictor: Yes, integrated with their dynamic tariffs (Agile Octopus).
  - Recommendations: Strong, especially around time-shifting to cheap half-hours. Their Agile tariff is the closest thing to what your ToU
  recommendation does.
  - Gap vs you: UK-only, utility-bundled. Different tariff structure entirely.

  Smappee (EU, ~EUR 250+)

  - Per-appliance monitoring: Yes, NILM-based, marketed for EU homes.
  - Bill predictor: Yes.
  - Recommendations: Solar/EV-focused — their business has pivoted toward solar self-consumption optimisation.
  - Gap vs you: EU tariffs, EU appliance mix.

  TP-Link Tapo / Xiaomi / Tuya smart plugs (sold in Malaysia)

  - Per-appliance monitoring: Yes, but only for the one appliance plugged into the smart plug. Per-plug, not whole-home.
  - Bill predictor: Crude — usually just kWh × flat rate in the app. No TNB tariff structure.
  - Recommendations: None worth mentioning. It's a measurement product, not an advisory product.
  - Gap vs you: Can't see the whole home. Doesn't aggregate. No ML.

  myTNB app (Malaysia, official)

  - Per-appliance monitoring: No.
  - Bill predictor: Limited — shows your past bills and current month consumption from smart meters where deployed. Some "usage trend"
  graphs.
  - Recommendations: Generic tips ("turn off lights"), not personalised, not appliance-aware.
  - Gap vs you: This is the most relevant comparison for judges. myTNB is what a Malaysian user currently has access to, and it does almost
   none of what you do.

  The honest summary table

  | Capability | Sense | Emporia | Bidgely | Smappee | Smart plugs | myTNB | **WattsEye** |
  |---|---|---|---|---|---|---|---|
  | Per-appliance breakdown | NILM | per-circuit | NILM | NILM | per-plug | No | **NILM + dedicated AC** |
  | Bill prediction | Flat US rate | Flat US rate | Utility-licensed | EU rate | Flat | Past bills only | **TNB RP4 full structure** |
  | Recommendations | Light | Minimal | Strong (B2B) | Solar-focused | None | Generic | **Situation-typed, audited** |
  | Inverter AC handling | Weak (pure NILM) | OK (dedicated clamp, no AI) | Unknown | Weak | N/A | N/A | **Hybrid — explicit design** |
  | Available in Malaysia | No (import) | No (import) | No (B2B only) | No | Yes | Yes (free) | **Yes** |
  | ToU tariff decision | No (US) | No | Utility-dep. | No | No | No | **Yes** |

  What this means for your pitch

  Don't claim category novelty. Claim three specific gaps:

  1. "Sense and Emporia exist but aren't sold here, and even if imported, they don't model TNB RP4 tariff — so a Malaysian user gets a
  US-shaped product."
  2. "Smart plugs are available locally but only see one appliance at a time and don't give recommendations."
  3. "myTNB shows your past bill but doesn't tell you what to do about it. We sit in the gap between the smart-plug ecosystem and the
  utility app."

  That positions WattsEye as the Malaysia-localised consumer energy advisor that doesn't currently exist, which is true and defensible —
  instead of "blue ocean," which a knowledgeable judge will challenge.

  One thing worth doing before the pitch

  Open the myTNB app yourself (or have a teammate screenshot it) and put one slide side-by-side: what myTNB shows you today vs what
  WattsEye shows you. That single comparison does more work than any "competitive landscape" slide because it grounds   Why myTNB-first is the right anchor

  Three reasons it works:

  1. The judges have probably used it. Most Malaysians with a TNB account have opened myTNB at least once. That means your comparison lands
   on lived experience, not abstract feature tables. Sense screenshots are foreign and theoretical; myTNB screenshots are "yeah, that's
  what I see every month."
  2. It sets the baseline at "what's actually available to a Malaysian consumer today." That's the honest frame. A user choosing between
  options doesn't get to import a Sense unit — they get myTNB and maybe a Tuya plug. If WattsEye is dramatically better than that realistic
   baseline, you win. Comparing against Sense forces you to fight a product the user can't even buy.
  3. It reframes the question the judges ask themselves. Instead of "is this better than Sense?" (hard — Sense has 10 years of
  engineering), they ask "is this better than myTNB?" (easy — yes, by a wide margin, and visibly so).

  Is this "trapping" the judges?

  Slightly, but it's legitimate framing, not deception. The trick only becomes dishonest if you hide the international competitors. If you
  mention them transparently and explain why myTNB is the right baseline, you've made an argument — not a sleight of hand. Judges respect a
   well-framed argument; they punish framing that feels evasive.

  The line you don't cross: never let a judge feel they had to pull the international comparison out of you. Volunteer it. That converts
  the framing from "trap" to "thesis."

  Recommended slide structure

  Slide N — "What Malaysian consumers have today"
  - Big screenshot of myTNB
  - Three bullets of what it does (past bill, basic trend, generic tips)
  - Three bullets of what it doesn't do (appliance-level, real-time, actionable, anomaly detection)
  - One line: "This is the baseline. Every Malaysian TNB customer has access to this and nothing more."

  Slide N+1 — "What WattsEye adds on top"
  - Same visual structure, your product
  - The diff is obvious and visceral

  Slide N+2 (optional, 30 seconds) — "Global context"
  - Small grid: Sense, Emporia, Bidgely, Smappee
  - One line each: "Exist overseas, not sold here, and not localised for TNB tariff or tropical loads."
  - Conclusion line: "The category is proven in the US and EU. WattsEye is the version built for Malaysia."

  That structure does three jobs at once:
  - Anchors the comparison at a baseline the judges know
  - Pre-empts the "what about Sense?" question before it's asked
  - Positions you as the Malaysia-localised version of a proven global category — which is a much stronger story than "blue ocean" and much
   stronger than "we have a feature Sense doesn't have."

  What to say out loud during the pitch

  The verbal framing matters as much as the slides. Two specific lines worth memorising:

  ▎ "The realistic comparison isn't Sense or Bidgely — those aren't available to Malaysian consumers. The realistic comparison is myTNB,
  ▎ which is what every TNB customer already has."

  That line lets you control the frame without sounding evasive.

  ▎ "The category is real. Sense, Bidgely, and Smappee prove people pay for this overseas. The gap is that none of them work for Malaysia —
  ▎  wrong tariff, wrong appliances, wrong assumptions about routine. WattsEye is the local version."

  That line acknowledges the international space transparently and converts it into evidence for your market thesis. Now Sense's existence
  becomes your argument, not your threat.

  One trap to avoid

  Don't make the myTNB comparison feel like "we're better than a government app" — that can read as either obvious (so what?) or arrogant
  (TNB has 11 million customers and you have a prototype). Frame it as "myTNB shows you the bill; we help you change the bill." Different
  jobs, not better/worse at the same job. That's the respectful, defensible framing.

  Net guidance

  Yes — lead with myTNB. It's not a trap, it's correct positioning. International competitors get one slide late in the deck, mentioned
  transparently, and converted from a threat into proof that the category works. The thesis becomes: a proven global category, localised
  for a market that currently has nothing. That's a clean story judges will remember.
the gap in something
  the judges have probably used themselves.




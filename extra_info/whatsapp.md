# WhatsApp Integration

## 1. App vs WhatsApp — different jobs, complementary

WhatsApp does not replace the in-app Coach tab. It's the *push channel* for cards that need attention now; the app is the *browse surface* for depth and audit.

| Channel | Job | Cardinality |
|---|---|---|
| App (Coach tab) | Browseable, auditable, depth surface. All 12 cards, expandables, math, history. | User opens when they want. |
| WhatsApp | Push channel. Reaches the user without them opening anything. Only cards that need immediate attention. | System sends when something material happens. |

Contradiction only happens if WhatsApp tries to be a second UI and ships all 12 archetypes — that becomes spam. Keep the split clean.

## 2. What goes through WhatsApp (subset, not all 12)

Filter every archetype by: *would a reasonable person want their phone to buzz for this?*

| # | Archetype | Why it earns the push |
|---|---|---|
| 1 | left_on_empty | Time-sensitive — value drops once you're home. |
| 5 | rp4_tier_cliff | Threshold crossing — actionable only within the current billing cycle. |
| 11 | anomaly_with_action | By definition unusual; user needs to know now. |
| 7 | bill_trending_high | Mid-cycle digest trigger, once per month. |

Plus **1 weekly digest** (Sunday morning) covering the rest of the week's secondary insights. Opt-in, one message.

The other 8 archetypes (phantom_standby, simultaneous_peak_load, tou_switch, peak_window_shift, comparative_regression, routine_shift, weather_correlated_ac, inefficient_upgrade) stay in-app only — they're advisory, slow-burn, or context-rich.

Total: **4 push triggers + 1 weekly digest** — sustainable, never spammy.

## 3. LLM for tone (Manglish), templates for numbers

Hybrid model — same rule as in-app narrative summaries:

```
Structured Card (from templates.py)          ← deterministic, has numbers
        ↓
LLM rephrases tone + injects Manglish        ← stylistic only
        ↓
Final WhatsApp message
```

**LLM is allowed to:** rephrase headline conversationally, add light Manglish ("aircon", "lah", "la"), soften tone, vary phrasing day-to-day.

**LLM is NOT allowed to:** generate or modify any number (RM, kWh, minutes, watts), invent appliances or evidence not in the structured input, recommend a different action.

**System prompt sketch:**

> *"You are WattsEye's WhatsApp assistant. Rephrase the input card into a casual, friendly WhatsApp message in English with light Manglish flavour. Use the exact numbers from the card — never invent or change them. Keep it under 4 short lines. End with a question that the user can answer with Yes/No/Later."*

**Example output (LLM):**

```
Eh, your aircon dah jalan 71 min but room empty already since 2:19 PM.
At your usual pattern, this kind of waste cost about RM 10/month.

Want me to turn it off + set auto-off after 20 min empty next time?

Reply: YES / NO / LATER
```

vs cold template:

```
WattsEye alert: AC running in empty room.
AC ran 71 min after the room emptied at 14:19. Cost: ~RM 10/month.
Action: enable auto-off after 20 min empty.
[ Do this ] [ Remind me ] [ Not useful ]
```

The Manglish version is warmer and uniquely Malaysian — judges notice it instantly. Numbers still templated, so it's defensible.

**Cost:** at hackathon volume (1 user × ~4 pushes/week), an LLM call is fractions of a cent. Haiku or GPT-4o-mini handles this trivially.

## 4. Analysing user responses — three options

| Option | Description | Verdict |
|---|---|---|
| A. Keyword matcher | String-match yes/no/later + bilingual aliases (boleh, nanti). ~30 lines. | **Recommended for hackathon.** Honest, auditable, handles 90%+. |
| B. LLM intent classifier | Pass reply + card to LLM, return `{intent, confidence}`. ~50 lines, fractions of a cent per reply. | Modest upgrade. Roadmap. |
| C. Full conversational agent | Multi-turn dialogue, "why?" follow-ups, configuration. | Skip for hackathon — real product engineering. |

**Option A sketch:**

```python
reply_lower = reply.strip().lower()
if any(w in reply_lower for w in ("yes", "ok", "y", "boleh", "do it")):
    action = "accept"
elif any(w in reply_lower for w in ("no", "n", "skip", "not useful", "x")):
    action = "dismiss"
elif any(w in reply_lower for w in ("later", "remind", "tomorrow", "nanti")):
    action = "snooze"
else:
    action = "unknown"  # follow up: "didn't catch that — try YES / NO / LATER"
```

If a judge asks "could you handle free-text replies?" → *"Yes, that's one LLM call away. We kept it strict for the demo so every action is auditable."*

## 5. Full message catalog (everything WhatsApp sends)

| Trigger | Message type | Frequency |
|---|---|---|
| Real-time alert (archetypes 1, 5, 11) | Action card with YES/NO/LATER | As they fire, max ~3/week |
| Weekly digest (Sunday) | Top 3 insights of the week, no questions | 1/week |
| Acknowledgement | "Got it — auto-off enabled. Saved you about RM 9/month." | After user replies YES |
| Mid-cycle bill warning (archetype 7) | "Your bill is trending +25% — here's the top driver." | Once per month at day 15 |
| Anomaly (archetype 11) | "Unusual activity at 2 AM — water heater. Check timer?" | When IF flags |

Five message types total. No FAQ bot, no help menu, no general chat.

## 6. Implementation options for the demo

| Option | Pros | Cons |
|---|---|---|
| Twilio WhatsApp Sandbox | Real WhatsApp, free for sandbox, judge's phone can opt-in by sending a code | Sandbox only — production needs Meta approval |
| WhatsApp Business Cloud API (Meta direct) | Free 1000 msgs/month, real production path | Setup takes 1–2 days, need Meta business account |
| Pure mock in demo HTML | Zero setup, controlled visual | Doesn't *feel* real to judges |

**Recommendation: Twilio WhatsApp Sandbox.** Have the judge type a code on their own phone during the demo and watch a real WhatsApp message arrive from your system. That moment — a real notification, in Manglish, on their actual lock screen, with the real RM figure — is a 10× stronger demo than any in-app card. Worth the 1 hour of Twilio setup.

## 7. One-line pitch addition

> *"Coach delivers actionable insights through the app for browsing, and through WhatsApp in Manglish for moments that need attention now — one structured pipeline, two channels, never more than four pushes a week."*

Sharp product statement. Another thing no foreign competitor does.


Right call — Meta Cloud API has a generous free tier and doesn't need a card. Here's the path.

  Setup steps (you do these — ~30-45 min)

  1. Meta Business account

  - Go to https://business.facebook.com → "Create account" (free, uses your Facebook login)
  - Name it anything (e.g., "WattsEye")

  2. Create a Meta App

  - Go to https://developers.facebook.com/apps → "Create app"
  - Use case: Other → Type: Business
  - Link it to the Business account you just made

  3. Add WhatsApp product

  - In your new app dashboard → "Add product" → find WhatsApp → "Set up"
  - Meta gives you:
    - A test phone number (their +1 555 ... number — like Twilio sandbox)
    - A Phone Number ID (long number — copy this)
    - A WhatsApp Business Account (WABA) ID (copy this)
    - A temporary 24-hour access token (copy this — you'll regenerate later)

  4. Add your phone as test recipient

  - In WhatsApp panel → "API Setup" → "To" field → "Manage phone number list"
  - Add your number (+60195613440) → Meta sends you a WhatsApp verification code → enter it
  - You can add up to 5 test recipients total (your phone, judge's phone, etc.) — all free

  5. Test send from Meta's dashboard

  - Still in "API Setup" → click "Send message" button
  - A "hello_world" template message lands on your phone within 5 seconds
  - Confirms the setup works before you touch code

  6. Save these 4 values

  META_PHONE_NUMBER_ID=<the long ID Meta showed>
  META_ACCESS_TOKEN=<the temporary token, regenerate later>
  META_WABA_ID=<your WhatsApp Business Account ID>
  META_RECIPIENT=60195613440          (no + or 'whatsapp:' prefix)

  7. Permanent token (later, not needed for hackathon)

  The temp token expires in 24h. For permanent: Business Settings → System Users → create one with WhatsApp permissions →
  generate a token that never expires. Skip for now — 24h temp is fine.

  ---
  Code side — I can do this now

  I'll add a parallel meta.py module so you can swap providers via env var. Same send_card_via_whatsapp() calling
  interface, different driver underneath. Want me to:

  Option A — Replace Twilio entirely with Meta (cleaner)
  Option B — Make it pluggable (WHATSAPP_DRIVER=twilio | meta env var, both work)

  For a hackathon where you've already proven Twilio works, Option A is simpler. Less code to maintain. Twilio's done its
  job demonstrating the integration to me; Meta becomes the real one.

  If you say go, I'll:
  1. Rewrite ML/insights/coach/whatsapp.py to call Meta's Graph API
  2. Rewrite ML/insights/coach/whatsapp_webhook.py to handle Meta's JSON webhook format + GET verification challenge
  3. Update .env.example with Meta env vars
  4. Keep the same external interface (send_card_via_whatsapp, push_eligible_cards) so nothing else changes

  The 2-stage classifier (keyword + Gemini fallback) and rate limiting stay identical — those don't depend on which
  provider sends the message.

  Two things to know about Meta specifically:

  1. Free-form messages need a recent user-initiated message in the conversation (within 24h). For the demo: have your
  phone send any message to the Meta number first ("hi"), then your alerts can flow freely for 24h. Same window concept as
  Twilio.
  2. Template messages bypass the 24h window but need pre-approval (3-7 days). Skip for hackathon — the 24h conversation
  window is enough.

  Tell me when you've done steps 1-5 and copied the 4 values. I'll wire the code while you wait, ready to drop your env
  vars in.



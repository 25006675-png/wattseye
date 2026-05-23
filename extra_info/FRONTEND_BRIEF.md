# WattsEye — Frontend Brief (Flutter)

**Audience:** Flutter dev building the WattsEye mobile companion app.
**Reference render:** `prototype/mobile-dashboard.html` — open it in a browser to see the intended visual feel and information density. Use it as inspiration, **not** as a pixel-perfect spec.

---

## 1. Goal

Build the mobile companion app for the WattsEye Pi. The app shows live appliance usage, projected TNB bill, and ranked recommendations from the Coach engine. It does **not** do any ML on-device — all data comes from the Pi over LAN/cloud via a small JSON API.

You are responsible for:
- Native-feeling Flutter UI (Material 3 — use the platform idioms, not a copy of the HTML)
- Navigation, scroll, transitions
- Reading the JSON contracts in §6 and rendering them
- Local UI state (expanded/dismissed/acted cards)

You are **not** responsible for:
- ML, tariff math, recommendation logic — all backend
- Authentication backend (UI stubs are fine)
- Push delivery — WhatsApp goes through Twilio server-side

---

## 2. Information architecture

Five tabs in a bottom nav bar. Order matters — left-to-right reflects daily use frequency.

| # | Tab | Job |
|---|---|---|
| 1 | **Dashboard** | What's happening *now*. Live power, active appliances, today's cost. |
| 2 | **Coach** | What you should *do* about it. Ranked recommendation cards. |
| 3 | **Bill** | Where the money *goes*. TNB RP4 breakdown, ToU comparison, EEI band. |
| 4 | **History** | What *happened*. Bill trend, appliance breakdown, waste history. |
| 5 | **Profile** | Account, household, hardware status, data, settings. |

Use a `BottomNavigationBar` (Material 3). Active tab uses the primary colour; inactive uses muted.

---

## 3. Design tokens

Set these in `lib/theme.dart` as a single `AppTheme` class. **Do not hardcode hex values anywhere else.**

### Colour

| Token | Hex | Usage |
|---|---|---|
| `primary` | `#3f7be0` | Active states, primary buttons, links |
| `text` | `#1a2233` | Primary text |
| `muted` | `#6b7280` | Secondary text, captions, icons |
| `surface` | `#ffffff` | Card background |
| `background` | `#f5f7fa` | Page background |
| `divider` | `#eef0f3` | Thin separators inside cards |
| `green` | `#2f9c5b` | Savings, success, linked status |
| `amber` | `#d4a02a` | Warnings, drift |
| `red` | `#c44` | High severity, destructive actions |

**Recommendation family colours** (used for card left-border + small tag chip):

| Family | Border | Tag bg | Tag text |
|---|---|---|---|
| waste | `#e07b3f` | `#fceee1` | `#8a4515` |
| tariff | `#3f7be0` | `#e3edfb` | `#1d4a99` |
| forecast | `#a23fe0` | `#ede1fb` | `#5a1d99` |
| context | `#3fa6e0` | `#e1f0fb` | `#155a8a` |
| capital | `#2f9c5b` | `#dff0e6` | `#195e34` |

### Type

Use a single sans (`Inter` or system default). Define these in `theme.textTheme`:

| Style | Size / weight | Line height | Use |
|---|---|---|---|
| `titleLarge` | 22 / 700 | 1.2 | Tab page titles |
| `titleMedium` | 17 / 700 | 1.2 | Card titles, section headers |
| `bodyMedium` | 14 / 400 | 1.45 | Body copy |
| `bodySmall` | 13 / 400 | 1.4 | Card impact paragraphs |
| `labelSmall` | 11 / 500 | 1.3 | Captions, metadata |
| `labelOverline` | 10 / 700 (letterspaced 0.8) | 1.2 | Section labels ("HOUSEHOLD") |

### Spacing scale

`4 · 8 · 12 · 16 · 24 · 32`. Use these only; no arbitrary paddings.

### Component shapes

- Cards: `BorderRadius.circular(8)`, padding `EdgeInsets.all(16)`, drop shadow `BoxShadow(blurRadius: 8, color: black 6%)`
- Tags / chips: `BorderRadius.circular(4)`, padding `EdgeInsets.symmetric(horizontal: 7, vertical: 3)`
- Buttons: standard Material 3
- Bottom nav: standard Material 3

---

## 4. Critical UX pattern — list-detail, not inline expand

**Most important interaction decision.** The HTML reference uses inline expandables for "Why this appeared" and "How we calculated this." That works on web but is wrong for mobile.

**Use list-detail navigation:**

- **Coach tab** = `ListView` of *compact* card summaries. Each summary shows: family tag, severity tag, headline (1 line), impact (2 lines, truncated), saving amount badge.
- **Tap a card** → `Navigator.push` a `CardDetailScreen` that shows full impact, action box, the three buttons (Do this / Remind me / Not useful), and the two collapsible sections (Why / Math).
- Back button returns to list. List reflects updated state (acted = green tick + struck-through saving; dismissed = greyed out).

This is the Gmail / Apple Mail / Slack pattern — users already know it. **Do not** stack 12 fully-expandable cards on one screen.

Top 2 cards (surfaced) get a slightly larger card variant; the other 10 use a denser compact variant. Same data, two densities.

---

## 5. Per-screen specs

### 5.1 Dashboard

**Above the fold:**
- Big live power number (e.g. *1.8 kW*) with subtle pulse animation when changing
- Today's cost so far (RM amount)
- Projected bill end-of-month
- "Home / Away" occupancy badge

**Below:**
- Per-appliance list (AC, fridge, kettle, etc.) — `ListTile` with watts + today's RM
- A "what's happening now" status line (e.g. *"AC on, room empty 14 min — Coach is watching"*)

Pull-to-refresh re-fetches dashboard state.

### 5.2 Coach

- Header: "12 active insights · Potential RM 47/month · Already saved RM 2.72"
- Section: "Top recommendations now" (top 2 surfaced cards, full-width)
- Section: "More insights" (remaining cards, compact)
- Tap any card → `CardDetailScreen`
- Filter chip row (optional v2): tap a family chip to filter to that family

### 5.3 Coach card detail screen

`Scaffold` with `AppBar(title: 'Recommendation')`:
- Family tag + severity tag at top
- Headline (title text)
- Impact paragraph
- Action card (boxed, light grey bg): label "Try this", action text, saving + effort + confidence
- Three action buttons (full-width primary "Do this", secondary "Remind me", text "Not useful")
- `ExpansionTile` × 2: "Why this appeared" (bulleted evidence) + "How we calculated this" (monospace math lines)

### 5.4 Bill

- Top card: projected bill with tariff badge + full TNB RP4 breakdown (Generation / Capacity / Network / EEI / AFA / Retail / Total — one row each)
- Card: Standard vs ToU comparison (two side-by-side panels with the recommended one highlighted)
  - "Preview as ToU" toggle button (display only) + "See Coach to apply →" button that navigates to the `tou_switch` card detail
- Card: EEI band meter (horizontal progress bar with cliff markers)
- Card: tariff schedule reference rows

Cross-link rule: any Bill-tab callout that has a matching Coach archetype shows a "See Coach for action →" button that navigates to that specific card detail.

### 5.5 History

- Bill trend bar chart (last 7 days, stacked by appliance)
- Appliance breakdown list (RM per appliance month-to-date)
- Waste history list (events + cost)

### 5.6 Profile

Settings-page style. Grouped sections:

| Section | Rows |
|---|---|
| (Header) | Avatar + name + email |
| Household | Address · Weather location · Household size · Home type |
| TNB Account | Account number (masked) · Tariff plan · Smart meter linked · myTNB linked |
| Coach & Notifications | WhatsApp number (masked) · Push frequency · Language · Quiet hours |
| Hardware | Pi status · Main clamp · AC clamp · mmWave · Firmware |
| Data | Local storage · Cloud sync · Export · Clear local data |
| Account | Help · Privacy · Sign out |

Use `ListTile` with subtle right chevron for actionable rows; static value rows have no chevron. Stub all actions with `SnackBar` notifications — they don't need to work in this build.

---

## 6. Data contracts

All endpoints return JSON. The backend (Python, `ML/insights/coach/coach_engine.py`) will host these via a small FastAPI server on the Pi. The Flutter app polls every 10–30 seconds for live state and on tab open for slower data.

### `GET /api/dashboard`

```json
{
  "timestamp": "2026-05-22T15:30:00+08:00",
  "live_power_w": 1850,
  "today_cost_rm": 4.97,
  "projected_bill_rm": 149.18,
  "occupancy_state": "away",
  "occupancy_since": "2026-05-22T14:19:00+08:00",
  "active_appliances": [
    {"name": "ac", "watts": 1200, "today_kwh": 8.4, "today_rm": 2.68},
    {"name": "fridge", "watts": 110, "today_kwh": 2.6, "today_rm": 0.83}
  ]
}
```

### `GET /api/coach/cards`

Returns the list of `Card` objects from `coach_engine.generate_cards()` → `cards_to_json()`.

```json
[
  {
    "archetype_id": 1,
    "archetype_key": "left_on_empty",
    "family": "waste",
    "severity": "high",
    "appliance": "ac",
    "timestamp": "2026-05-22T15:30",
    "headline": "AC running in empty room",
    "impact_text": "AC ran 71 min after the room emptied at 14:19. At your current pattern, this costs about RM 10/month.",
    "action_text": "Enable auto-off after 20 min empty.",
    "saving_text": "Expected saving: RM 10/month",
    "effort_text": "Low effort",
    "confidence_label": "High confidence",
    "why_lines": [
      "Occupancy: Room empty since 14:19 (71 min).",
      "NILM: AC drawing 1,200W.",
      "K-Means phase: work (14:00–17:00).",
      "Routine baseline: AC normally OFF during work phase (observed 14/14 weekdays)."
    ],
    "math_lines": [
      "1,200W × 71 min ÷ 60 = 1.42 kWh wasted this event",
      "Event cost via TNB RP4 marginal pricing: RM 0.57",
      "Weekly frequency 4 × 4.345 weeks/month → RM 9.85/month"
    ],
    "impact_rm_monthly": 9.85,
    "confidence": 0.85,
    "score": 3.66,
    "rank": 6,
    "surfaced": false
  }
]
```

`surfaced: true` → render as a top-section card. `surfaced: false` → secondary section.

### `POST /api/coach/cards/{archetype_key}/action`

Body: `{"action": "do" | "remind" | "dismiss"}`. Returns `{"ok": true}`.

### `GET /api/bill`

Shape mirrors what's displayed in the HTML Bill tab. See `ML/insights/tnb_tariff.py` `BillBreakdown` dataclass for line items.

### `GET /api/history`

Last 7 days of daily cost + per-appliance breakdown. Simple aggregation.

---

## 7. State management

- **Riverpod** (or **bloc** if you prefer) — pick one, use it everywhere.
- One provider per endpoint above. Coach cards provider exposes a `markAction()` method that POSTs and optimistically updates local state.
- Tab state in the bottom nav is a `StateProvider<int>`.
- Don't use `setState` outside of trivial local widgets.

---

## 8. Polish targets (in priority order)

If you have time after the spec above is met:

1. **Live tick** — dashboard numbers update smoothly every 2s (use `AnimatedSwitcher` for the kW value)
2. **Card action animations** — tapping "Do this" runs a brief check-mark animation, then the card collapses into the list with a strikethrough
3. **Pull-to-refresh** on Dashboard / Coach / Bill / History
4. **Skeleton loaders** on first launch while data fetches
5. **Empty state** for Coach ("All insights actioned — nothing new") if list is empty
6. **Tag chips on Coach are tappable** to filter by family

Do NOT spend time on: dark mode, onboarding flow, complex animations, custom illustrations.

---

## 9. Acceptance criteria for the demo

A judge picks up the phone and within 30 seconds should be able to:

1. See live home power on the Dashboard tab.
2. Tap Coach, see 2 top recommendations + a longer list below.
3. Tap a recommendation, read the full detail with the math chain.
4. Tap "Do this" and see the list reflect the action.
5. Tap Bill, see a TNB RP4 breakdown that visibly differs from a flat-rate calc.
6. Tap Profile and see a real-looking settings page.

If all six of those work smoothly on a real device, the frontend is done.

---

## 10. Open questions to confirm with backend (me)

- Final base URL for the API (LAN IP of Pi, or proxied through cloud?)
- Auth: bearer token in header? Simple shared secret for demo?
- Polling interval for Dashboard live data (suggested 5s)
- Whether weather forecast comes through the dashboard endpoint or a separate one

Send a Slack message before you start implementing if any of these are unclear. Better to spend 5 minutes asking than 5 hours rebuilding.

---

**Reference render:** `prototype/mobile-dashboard.html`
**Backend pipeline:** `ML/insights/coach/`
**Data philosophy:** `recommendation.md`
**WhatsApp side:** `whatsapp.md`

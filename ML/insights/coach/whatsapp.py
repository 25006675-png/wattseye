"""WhatsApp delivery for Coach cards via Twilio.

Runs on the Pi as part of the Coach pipeline. The Pi never hosts WhatsApp
itself — it POSTs to Twilio's REST API; Twilio delivers the message and
relays replies via webhook.

Flow:

  Coach engine generates a Card
        ↓
  send_card_via_whatsapp(card)
        ↓
  (optional) LLM rephrases into Manglish using the structured Card as input
        ↓
  Twilio REST API: POST /Messages.json
        ↓
  Twilio → user's WhatsApp
        ↓
  user replies "YES" / "NO" / "LATER"
        ↓
  Twilio POSTs to our /webhook/whatsapp endpoint (see whatsapp_webhook.py)

Setup (one-time, on Twilio side):
  1. twilio.com → free account
  2. Console → Messaging → Try it out → Send a WhatsApp message
  3. Note ACCOUNT_SID, AUTH_TOKEN, sandbox WhatsApp number (e.g. +14155238886)
  4. Text the join code from your phone to opt in
  5. Set env vars in .env on the Pi (see SETUP_ENV_VARS below)

Only archetypes 1 (left_on_empty), 5 (rp4_tier_cliff), 11 (anomaly_with_action)
trigger a push by default. Everything else stays in-app only. See whatsapp.md
for the rationale.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .situations import Card

# Path imported by the dotenv loader below
_THIS = Path(__file__)

log = logging.getLogger("wattseye.whatsapp")

# Env vars the Pi must have set (in .env or systemd unit)
SETUP_ENV_VARS = [
    "TWILIO_ACCOUNT_SID",       # ACxxxxxxxxxxxxxxxxxxxx
    "TWILIO_AUTH_TOKEN",        # 32-char hex
    "TWILIO_WHATSAPP_FROM",     # e.g. "whatsapp:+14155238886" (sandbox)
    "TWILIO_WHATSAPP_TO",       # e.g. "whatsapp:+60123456789"
]


def _load_dotenv() -> None:
    """Lightweight .env loader — no python-dotenv dependency.

    Looks in the project root (parents[3]) for a .env file and loads KEY=VALUE
    lines into os.environ if they're not already set.
    """
    project_root = Path(__file__).resolve().parents[3]
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

# Archetypes that earn a WhatsApp push. See whatsapp.md §2 for rationale.
PUSH_ARCHETYPES = {"left_on_empty", "rp4_tier_cliff", "anomaly_with_action", "bill_trending_high"}

# Minimum minutes between any two pushes — never spam the user.
MIN_PUSH_INTERVAL_MIN = 60

# Sent-log path — used by rate limiter + dedup
SENT_LOG_PATH = Path(__file__).resolve().parent / "_whatsapp_sent.json"


# ---------- Twilio REST client (no SDK dependency) ----------

TWILIO_API_BASE = "https://api.twilio.com/2010-04-01"


@dataclass(frozen=True)
class TwilioConfig:
    account_sid: str
    auth_token: str
    from_number: str             # "whatsapp:+1..."
    default_to: str              # "whatsapp:+60..."

    @classmethod
    def from_env(cls) -> "TwilioConfig | None":
        try:
            return cls(
                account_sid=os.environ["TWILIO_ACCOUNT_SID"],
                auth_token=os.environ["TWILIO_AUTH_TOKEN"],
                from_number=os.environ["TWILIO_WHATSAPP_FROM"],
                default_to=os.environ["TWILIO_WHATSAPP_TO"],
            )
        except KeyError as e:
            log.warning("Missing env var %s — WhatsApp send disabled", e)
            return None


def _twilio_send(cfg: TwilioConfig, body: str, to: str | None = None) -> dict:
    """Low-level Twilio REST call. Returns parsed JSON on success."""
    url = f"{TWILIO_API_BASE}/Accounts/{cfg.account_sid}/Messages.json"
    payload = urllib.parse.urlencode({
        "From": cfg.from_number,
        "To": to or cfg.default_to,
        "Body": body,
    }).encode()
    auth = b64encode(f"{cfg.account_sid}:{cfg.auth_token}".encode()).decode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "WattsEye/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


# ---------- rate limiting / dedup ----------

def _load_sent_log() -> dict[str, str]:
    if not SENT_LOG_PATH.exists():
        return {}
    try:
        return json.loads(SENT_LOG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sent_log(log_dict: dict[str, str]) -> None:
    SENT_LOG_PATH.write_text(json.dumps(log_dict))


def _should_push(card: Card, now: datetime) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    if card.archetype_key not in PUSH_ARCHETYPES:
        return False, "archetype not in PUSH_ARCHETYPES"

    sent = _load_sent_log()

    # Per-archetype: no more than 1 push per archetype per 12 h
    last_for_arch = sent.get(card.archetype_key)
    if last_for_arch:
        delta = now - datetime.fromisoformat(last_for_arch)
        if delta < timedelta(hours=12):
            return False, f"already pushed this archetype {delta} ago"

    # Global: no two pushes within MIN_PUSH_INTERVAL_MIN
    last_any = sent.get("__last_any__")
    if last_any:
        delta = now - datetime.fromisoformat(last_any)
        if delta < timedelta(minutes=MIN_PUSH_INTERVAL_MIN):
            return False, f"global rate-limit (last push {delta} ago)"

    return True, "ok"


def _record_push(card: Card, now: datetime) -> None:
    sent = _load_sent_log()
    sent[card.archetype_key] = now.isoformat()
    sent["__last_any__"] = now.isoformat()
    _save_sent_log(sent)


# ---------- message rendering ----------

def render_message_template(card: Card) -> str:
    """Deterministic fallback message — used when no LLM is configured.

    Numbers come straight from the Card; this never hallucinates.
    """
    lines = [
        f"WattsEye alert: {card.headline}",
        "",
        card.impact_text,
        "",
        f"Try this: {card.action_text}",
        f"{card.saving_text} · {card.effort_text}",
        "",
        "Reply: YES (do it) / NO (dismiss) / LATER (snooze)",
    ]
    return "\n".join(lines)


# Language-specific system prompts. Numbers must always be preserved verbatim;
# only tone/wording changes.
_LANG_PROMPTS = {
    "en": (
        "You are WattsEye's WhatsApp assistant. Rephrase the input card into a "
        "casual, friendly WhatsApp message in clear English. "
        "Use the EXACT numbers from the card — never invent or change any "
        "number, appliance name, or recommended action. "
        "Keep it under 4 short lines plus the reply prompt. "
        "End with exactly: 'Reply: YES / NO / LATER'."
    ),
    "malay": (
        "You are WattsEye's WhatsApp assistant. Rephrase the input card into a "
        "casual, friendly WhatsApp message in Bahasa Malaysia. "
        "Use the EXACT numbers from the card — never invent or change any "
        "number, appliance name, or recommended action. Keep RM amounts and "
        "units (kWh, min) unchanged. Keep it under 4 short lines plus the "
        "reply prompt. End with exactly: 'Balas: YA / TIDAK / KEMUDIAN'."
    ),
    "mix": (
        "You are WattsEye's WhatsApp assistant. Rephrase the input card into a "
        "casual, friendly WhatsApp message in English with light Manglish / "
        "Malaysian slang flavour (e.g. 'aircon', 'lah', 'la', 'eh', 'dah', "
        "'tau'). Do not overuse — natural KL/PJ urban tone. "
        "Use the EXACT numbers from the card — never invent or change any "
        "number, appliance name, or recommended action. "
        "Keep it under 4 short lines plus the reply prompt. "
        "End with exactly: 'Reply: YES / NO / LATER'."
    ),
}


def _get_language() -> str:
    """Return one of 'en' | 'malay' | 'mix'. Defaults to 'mix'."""
    lang = os.environ.get("WATTSEYE_LANG", "mix").strip().lower()
    if lang not in _LANG_PROMPTS:
        log.warning("Unknown WATTSEYE_LANG=%r, defaulting to 'mix'", lang)
        lang = "mix"
    return lang


def _gemini_rephrase(card: Card, api_key: str, language: str) -> str:
    """Call Gemini REST API to rephrase the card. No SDK dependency."""
    system_prompt = _LANG_PROMPTS[language]
    user_payload = json.dumps({
        "headline": card.headline,
        "impact_text": card.impact_text,
        "action_text": card.action_text,
        "saving_text": card.saving_text,
        "effort_text": card.effort_text,
        "appliance": card.appliance,
    }, indent=2)

    model = "gemini-2.5-flash"
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": user_payload}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        # Gemini 2.5 reserves part of the budget for internal "thinking",
        # so we set a generous ceiling — actual reply stays short due to prompt.
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024,
                              "thinkingConfig": {"thinkingBudget": 0}},
    }).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "WattsEye/0.1"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
    return result["candidates"][0]["content"]["parts"][0]["text"].strip()


def render_message_via_llm(card: Card, language: str | None = None) -> str:
    """LLM rephrase via Gemini in the configured language.

    Provider: Google Gemini (free tier OK).
    Language: from `language` arg, else $WATTSEYE_LANG, else 'mix'.

    The LLM only ever receives the structured Card fields — never raw data,
    never numbers it could re-derive. The system prompt explicitly forbids
    changing numeric values. Falls back to the deterministic template on any
    failure (missing key, network error, rate limit).
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return render_message_template(card)

    lang = (language or _get_language())
    try:
        return _gemini_rephrase(card, api_key, lang)
    except Exception as e:
        log.warning("Gemini rephrase failed (%s); falling back to template", e)
        return render_message_template(card)


# ---------- public entrypoints ----------

def send_card_via_whatsapp(card: Card, *, now: datetime | None = None,
                           use_llm: bool = True, dry_run: bool = False) -> dict:
    """Send a Coach card to the configured WhatsApp number.

    Returns a dict describing what happened — useful for logging + the
    dashboard's "Sent: 2 min ago" indicator. Never raises; failures are
    captured in the return value.

    Args:
        card: the Coach Card to send
        now: override timestamp (for testing); defaults to datetime.now()
        use_llm: if True and ANTHROPIC_API_KEY is set, rephrase via LLM
        dry_run: if True, render but do not actually call Twilio
    """
    now = now or datetime.now()

    allowed, reason = _should_push(card, now)
    if not allowed:
        return {"sent": False, "reason": reason, "archetype": card.archetype_key}

    body = render_message_via_llm(card) if use_llm else render_message_template(card)

    if dry_run:
        return {"sent": False, "reason": "dry_run", "body": body, "archetype": card.archetype_key}

    cfg = TwilioConfig.from_env()
    if cfg is None:
        return {"sent": False, "reason": "missing twilio env vars", "body": body,
                "archetype": card.archetype_key, "setup_needed": SETUP_ENV_VARS}

    try:
        result = _twilio_send(cfg, body)
        _record_push(card, now)
        return {"sent": True, "twilio_sid": result.get("sid"),
                "archetype": card.archetype_key, "body": body}
    except Exception as e:
        log.error("Twilio send failed: %s", e)
        return {"sent": False, "reason": f"twilio error: {e}",
                "archetype": card.archetype_key, "body": body}


def push_eligible_cards(cards: list[Card], *, now: datetime | None = None,
                        use_llm: bool = True, dry_run: bool = False) -> list[dict]:
    """Push every eligible surfaced card. Called by the coach engine after rank()."""
    results = []
    for card in cards:
        if not card.surfaced:
            continue
        if card.archetype_key not in PUSH_ARCHETYPES:
            continue
        results.append(send_card_via_whatsapp(card, now=now, use_llm=use_llm, dry_run=dry_run))
    return results


# ---------- CLI smoke test ----------

if __name__ == "__main__":
    import argparse

    from .coach_engine import _demo_snapshot, generate_cards

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Render messages but don't call Twilio")
    parser.add_argument("--send", action="store_true",
                        help="Actually send — overrides --dry-run")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM rephrase, use deterministic template")
    args = parser.parse_args()

    cards = generate_cards(_demo_snapshot(), surface_count=4, include_weather=False)
    results = push_eligible_cards(
        cards,
        use_llm=not args.no_llm,
        dry_run=not args.send,
    )

    print(f"\n=== {len(results)} eligible push(es) ===\n")
    for r in results:
        print(f"  [{r['archetype']}] sent={r['sent']} reason={r.get('reason', '-')}")
        if "body" in r:
            print("  ---")
            for line in r["body"].splitlines():
                print(f"  | {line}")
            print()

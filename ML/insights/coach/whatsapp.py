"""WhatsApp delivery for Coach cards via the Meta WhatsApp Cloud API.

Runs on the Pi as part of the Coach pipeline. The Pi never hosts WhatsApp
itself — it POSTs to Meta's Graph API; Meta delivers the message and
relays replies via webhook.

Flow:

  Coach engine generates a Card
        ↓
  send_card_via_whatsapp(card)
        ↓
  (optional) LLM rephrases into Manglish using the structured Card as input
        ↓
  Meta Graph API: POST /{PHONE_NUMBER_ID}/messages
        ↓
  Meta → user's WhatsApp
        ↓
  user replies "YES" / "NO" / "LATER"
        ↓
  Meta POSTs JSON to our /webhook/whatsapp endpoint (see whatsapp_webhook.py)

Setup (one-time, on Meta side):
  1. business.facebook.com → create a (free) Business account
  2. developers.facebook.com/apps → create app (Other → Business)
  3. Add the WhatsApp product → note the Phone Number ID + access token
  4. Add your phone as a verified test recipient (up to 5, free)
  5. Set env vars in .env on the Pi (see SETUP_ENV_VARS below)

Note on the 24h window: free-form text messages only deliver if the recipient
has messaged the number within the last 24h. Have the phone send any message
to the Meta number first to open the window. Templates (e.g. hello_world)
bypass the window but need pre-approval — see send_template().

Only archetypes 1 (left_on_empty), 5 (rp4_tier_cliff), 11 (anomaly_with_action)
trigger a push by default. Everything else stays in-app only. See whatsapp.md
for the rationale.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .situations import Card

# Path imported by the dotenv loader below
_THIS = Path(__file__)

log = logging.getLogger("wattseye.whatsapp")

# Env vars the Pi must have set (in .env or systemd unit)
SETUP_ENV_VARS = [
    "META_ACCESS_TOKEN",        # EAA... (temp 24h or permanent system-user token)
    "META_PHONE_NUMBER_ID",     # long numeric ID from the WhatsApp API Setup page
    "META_RECIPIENT",           # e.g. "60195613440" (no '+' or 'whatsapp:' prefix)
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


# ---------- Meta WhatsApp Cloud API client (no SDK dependency) ----------

# Graph API version. Meta keeps versions live for ~2 years; bump when convenient.
META_GRAPH_VERSION = "v21.0"
META_GRAPH_BASE = "https://graph.facebook.com"


@dataclass(frozen=True)
class MetaConfig:
    access_token: str
    phone_number_id: str         # numeric ID, NOT the display phone number
    default_to: str              # bare digits, e.g. "60195613440"

    @classmethod
    def from_env(cls) -> "MetaConfig | None":
        try:
            return cls(
                access_token=os.environ["META_ACCESS_TOKEN"],
                phone_number_id=os.environ["META_PHONE_NUMBER_ID"],
                default_to=os.environ["META_RECIPIENT"],
            )
        except KeyError as e:
            log.warning("Missing env var %s — WhatsApp send disabled", e)
            return None


def _meta_post(cfg: MetaConfig, payload: dict) -> dict:
    """Low-level Graph API POST to the messages endpoint. Returns parsed JSON."""
    url = f"{META_GRAPH_BASE}/{META_GRAPH_VERSION}/{cfg.phone_number_id}/messages"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {cfg.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "WattsEye/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def _meta_send(cfg: MetaConfig, body: str, to: str | None = None) -> dict:
    """Send a free-form text message. Requires an open 24h conversation window."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to or cfg.default_to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    return _meta_post(cfg, payload)


def _meta_send_template(cfg: MetaConfig, template: str = "hello_world",
                        lang_code: str = "en_US", to: str | None = None) -> dict:
    """Send a pre-approved template message — bypasses the 24h window.

    Use 'hello_world' (always available) to confirm wiring before the window
    is open. Custom templates need Meta approval before they can be sent.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to or cfg.default_to,
        "type": "template",
        "template": {"name": template, "language": {"code": lang_code}},
    }
    return _meta_post(cfg, payload)


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
        use_llm: if True and GEMINI_API_KEY is set, rephrase via LLM
        dry_run: if True, render but do not actually call Meta
    """
    now = now or datetime.now()

    allowed, reason = _should_push(card, now)
    if not allowed:
        return {"sent": False, "reason": reason, "archetype": card.archetype_key}

    body = render_message_via_llm(card) if use_llm else render_message_template(card)

    if dry_run:
        return {"sent": False, "reason": "dry_run", "body": body, "archetype": card.archetype_key}

    cfg = MetaConfig.from_env()
    if cfg is None:
        return {"sent": False, "reason": "missing meta env vars", "body": body,
                "archetype": card.archetype_key, "setup_needed": SETUP_ENV_VARS}

    try:
        result = _meta_send(cfg, body)
        _record_push(card, now)
        msg_id = (result.get("messages") or [{}])[0].get("id")
        return {"sent": True, "message_id": msg_id,
                "archetype": card.archetype_key, "body": body}
    except Exception as e:
        log.error("Meta send failed: %s", e)
        return {"sent": False, "reason": f"meta error: {e}",
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
                        help="Render messages but don't call Meta")
    parser.add_argument("--send", action="store_true",
                        help="Actually send — overrides --dry-run")
    parser.add_argument("--no-llm", action="store_true",
                        help="Skip LLM rephrase, use deterministic template")
    parser.add_argument("--hello", action="store_true",
                        help="Send Meta's hello_world template to confirm wiring "
                             "(bypasses the 24h window) and exit")
    args = parser.parse_args()

    if args.hello:
        cfg = MetaConfig.from_env()
        if cfg is None:
            print(f"Missing env vars. Need: {', '.join(SETUP_ENV_VARS)}")
            raise SystemExit(1)
        try:
            res = _meta_send_template(cfg)
            print(f"hello_world sent -> id={(res.get('messages') or [{}])[0].get('id')}")
        except Exception as e:
            print(f"send failed: {e}")
            raise SystemExit(1)
        raise SystemExit(0)

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

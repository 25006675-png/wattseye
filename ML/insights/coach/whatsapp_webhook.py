"""Flask webhook endpoint that receives Meta WhatsApp Cloud API replies.

Two-stage classifier:

  1. Keyword matcher (fast, deterministic, free)
     yes | ok | y | boleh | do it       → accept
     no  | n | skip | not useful | x    → dismiss
     later | remind | tomorrow | nanti  → snooze

  2. Gemini classifier (fallback only, used when keyword matcher returns unknown)
     Returns {intent, confidence, reason}.

Confidence banding:
   ≥ 0.70 → act on the intent
   0.40-0.70 → echo confirmation ("You meant ... — reply YES to confirm")
   < 0.40 → treat as unknown; ask for clear YES / NO / LATER

This gives instant response on clear replies, and graceful handling of free-text
and Manglish/Malay variations that aren't in the keyword set ("tak nak",
"ok turn it off la", "k", etc.) without ever silently doing the wrong thing.

Meta differs from Twilio in three ways, all handled below:
  1. GET verification: when you subscribe the webhook, Meta sends a GET with
     hub.mode / hub.verify_token / hub.challenge. We echo hub.challenge back
     verbatim iff hub.verify_token matches $META_VERIFY_TOKEN.
  2. POST payloads are JSON (not form-encoded), nested under entry[].changes[].
  3. Replies are NOT returned in the HTTP response (no TwiML). We return 200 to
     ack receipt, then POST the acknowledgement back via the Graph API.

Deploy:
  - Run on the Pi on port 8080
  - Expose via ngrok (`ngrok http 8080`)
  - In the Meta App dashboard → WhatsApp → Configuration → Webhook:
      Callback URL: `https://<your-host>/webhook/whatsapp`
      Verify token: must equal $META_VERIFY_TOKEN
    then Subscribe to the `messages` field.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    from flask import Flask, Response, request
except ImportError:
    Flask = None  # type: ignore
    Response = None  # type: ignore
    request = None  # type: ignore

# Reuse the dotenv loader (import side-effect loads .env) + the Meta sender,
# so the webhook can POST acknowledgements back through the same Graph API path.
from .whatsapp import MetaConfig, _load_dotenv, _meta_send  # noqa: F401

log = logging.getLogger("wattseye.whatsapp.webhook")

ACTION_LOG_PATH = Path(__file__).resolve().parent / "_user_actions.json"


# ---------- Stage 1: keyword matcher ----------

ACCEPT_WORDS = {"yes", "ok", "okk", "okay", "okeh", "y", "boleh", "do it", "do", "go", "sure", "ya", "yea", "yup", "yeah"}
DISMISS_WORDS = {"no", "n", "skip", "not useful", "x", "stop", "tak", "tidak"}
SNOOZE_WORDS = {"later", "remind", "tomorrow", "nanti", "wait", "snooze", "kemudian"}


def classify_reply_keyword(reply: str) -> str:
    """Stage 1. Return 'accept' | 'dismiss' | 'snooze' | 'unknown'."""
    text = reply.strip().lower()
    if text in ACCEPT_WORDS or any(w in text for w in ACCEPT_WORDS if len(w) > 2):
        return "accept"
    if text in DISMISS_WORDS or any(w in text for w in DISMISS_WORDS if len(w) > 2):
        return "dismiss"
    if any(w in text for w in SNOOZE_WORDS):
        return "snooze"
    if text in {"y", "n", "x"}:
        return {"y": "accept", "n": "dismiss", "x": "dismiss"}[text]
    return "unknown"


# ---------- Stage 2: Gemini classifier (fallback) ----------

_GEMINI_CLASSIFY_PROMPT = """\
You classify the user's WhatsApp reply to an energy-saving recommendation.
The user can reply in English, Bahasa Malaysia, or Manglish (mixed casual).

Possible intents:
  - accept   : user wants the action applied (yes, ok, boleh, do it, go ahead)
  - dismiss  : user rejects the recommendation (no, tak nak, not now, skip)
  - snooze   : user wants to be reminded later (nanti, kemudian, tomorrow, busy)
  - question : user is asking for explanation / more info ("why?", "explain", "how come")
  - unknown  : reply is unclear, ambiguous, off-topic, or unparseable

Return ONLY a JSON object with this exact shape:
{
  "intent": "accept" | "dismiss" | "snooze" | "question" | "unknown",
  "confidence": <number from 0.0 to 1.0>,
  "reason": "<one short sentence explaining your classification>"
}

No prose, no markdown fences, JSON only.
"""


def _gemini_classify(reply: str) -> dict | None:
    """Stage 2. Returns {intent, confidence, reason} or None on failure."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    model = "gemini-2.5-flash"
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": reply}]}],
        "systemInstruction": {"parts": [{"text": _GEMINI_CLASSIFY_PROMPT}]},
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 256,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
        },
    }).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "WattsEye/0.1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        parsed = json.loads(text)
        if "intent" not in parsed or "confidence" not in parsed:
            return None
        return parsed
    except Exception as e:
        log.warning("Gemini classify failed (%s); falling back", e)
        return None


# ---------- combined classifier ----------

def classify_reply(reply: str) -> dict:
    """Two-stage classifier. Returns:
        {
          'intent': accept|dismiss|snooze|question|unknown,
          'confidence': float in [0, 1],
          'stage': 'keyword' | 'gemini' | 'fallback',
          'reason': str,
        }
    """
    kw = classify_reply_keyword(reply)
    if kw != "unknown":
        return {
            "intent": kw, "confidence": 0.99, "stage": "keyword",
            "reason": "matched keyword set",
        }

    gem = _gemini_classify(reply)
    if gem is not None:
        return {
            "intent": gem["intent"],
            "confidence": float(gem["confidence"]),
            "stage": "gemini",
            "reason": gem.get("reason", ""),
        }

    return {
        "intent": "unknown", "confidence": 0.0, "stage": "fallback",
        "reason": "no keyword match and Gemini unavailable",
    }


# ---------- action persistence ----------

def _load_actions() -> list[dict]:
    if not ACTION_LOG_PATH.exists():
        return []
    try:
        return json.loads(ACTION_LOG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return []


def _save_actions(actions: list[dict]) -> None:
    ACTION_LOG_PATH.write_text(json.dumps(actions, indent=2))


def record_user_action(archetype_key: str, classification: dict, raw_reply: str,
                       from_number: str) -> None:
    actions = _load_actions()
    actions.append({
        "timestamp": datetime.now().isoformat(),
        "archetype_key": archetype_key,
        "intent": classification["intent"],
        "confidence": classification["confidence"],
        "stage": classification["stage"],
        "reason": classification.get("reason", ""),
        "raw_reply": raw_reply,
        "from": from_number,
    })
    _save_actions(actions[-200:])


def _most_recent_pushed_archetype() -> str | None:
    sent_log = Path(__file__).resolve().parent / "_whatsapp_sent.json"
    if not sent_log.exists():
        return None
    try:
        data = json.loads(sent_log.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    last_any = data.get("__last_any__")
    if not last_any:
        return None
    for k, v in data.items():
        if k == "__last_any__":
            continue
        if v == last_any:
            return k
    return None


# ---------- acknowledgement composer (confidence-banded) ----------

_ACK_HIGH = {
    "accept":   "Got it - action will be applied. Track the saving in the WattsEye app.",
    "dismiss":  "Noted. WattsEye will lower this card priority for a week.",
    "snooze":   "Okay, will remind you tomorrow.",
    "question": "Good question - open the WattsEye app Coach tab for the full evidence and math.",
    "unknown":  "Didn't catch that - please reply: YES (do it) / NO (dismiss) / LATER (snooze).",
}

_ACK_MEDIUM = {
    "accept":   "I think you want to apply this - reply YES to confirm.",
    "dismiss":  "I think you want to dismiss this - reply NO to confirm.",
    "snooze":   "I think you want a reminder - reply LATER to confirm.",
    "question": "Looks like a question - open the WattsEye app for full details.",
}


def compose_ack(classification: dict) -> str:
    intent = classification["intent"]
    conf = classification["confidence"]
    if conf >= 0.70:
        return _ACK_HIGH.get(intent, _ACK_HIGH["unknown"])
    if conf >= 0.40 and intent in _ACK_MEDIUM:
        return _ACK_MEDIUM[intent]
    return _ACK_HIGH["unknown"]


# ---------- Meta payload parsing ----------

def extract_messages(payload: dict) -> list[dict]:
    """Pull inbound text messages out of Meta's webhook JSON.

    Meta nests messages under entry[].changes[].value.messages[]. The same
    webhook also delivers delivery/read *status* events (value.statuses) which
    carry no user text — those are ignored. Returns a list of
    {"from": <wa_id>, "text": <body>} for genuine inbound text messages.
    """
    out: list[dict] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                out.append({
                    "from": msg.get("from", ""),
                    "text": (msg.get("text") or {}).get("body", ""),
                })
    return out


def _send_ack(ack_text: str, to: str) -> None:
    """POST the acknowledgement back to the user via the Graph API.

    Best-effort: if Meta env vars are missing or the call fails, we log and
    move on — the inbound reply has already been recorded either way.
    """
    cfg = MetaConfig.from_env()
    if cfg is None:
        log.warning("ack not sent — Meta env vars missing")
        return
    try:
        _meta_send(cfg, ack_text, to=to or None)
    except Exception as e:
        log.warning("ack send failed (%s)", e)


# ---------- Flask app ----------

def create_app():
    if Flask is None:
        raise RuntimeError("flask not installed. pip install flask")

    app = Flask(__name__)

    @app.route("/webhook/whatsapp", methods=["GET"])
    def whatsapp_verify():
        # Meta webhook verification handshake.
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge", "")
        expected = os.environ.get("META_VERIFY_TOKEN")
        if mode == "subscribe" and expected and token == expected:
            log.info("webhook verified")
            return Response(challenge, mimetype="text/plain")
        log.warning("webhook verification failed (mode=%s token_match=%s)",
                    mode, token == expected)
        return Response("verification failed", status=403)

    @app.route("/webhook/whatsapp", methods=["POST"])
    def whatsapp_webhook():
        payload = request.get_json(silent=True) or {}
        messages = extract_messages(payload)
        if not messages:
            # Status callback (delivered/read) or non-text message — ack and skip.
            return Response(status=200)

        for msg in messages:
            from_number = msg["from"]
            body = msg["text"]
            log.info("whatsapp reply from=%s body=%r", from_number, body)

            archetype = _most_recent_pushed_archetype()
            classification = classify_reply(body)
            log.info("classified intent=%s conf=%.2f stage=%s reason=%r",
                     classification["intent"], classification["confidence"],
                     classification["stage"], classification.get("reason", ""))

            record_user_action(archetype or "unknown", classification, body, from_number)
            _send_ack(compose_ack(classification), from_number)

        return Response(status=200)

    @app.route("/healthz", methods=["GET"])
    def healthz():
        return {"ok": True, "service": "wattseye-whatsapp-webhook"}

    return app


# ---------- CLI ----------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--test", action="store_true",
                        help="Run the classifier against a set of test inputs and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    if args.test:
        TEST_INPUTS = [
            "YES", "no", "later", "LATER",          # clear keywords
            "ok turn it off la", "boleh boleh",      # Manglish accept
            "tak nak", "tidak mahu",                 # Malay dismiss
            "nanti la, busy",                        # Malay snooze
            "k",                                     # ambiguous
            "why is this happening?", "explain",     # question
            "don't bother me",                       # free-text dismiss
            "ya betul, do it",                       # mixed accept
            "lol what",                              # truly unknown
        ]
        print(f"{'INPUT':<40} {'STAGE':<10} {'INTENT':<10} {'CONF':<6} REASON")
        print("-" * 110)
        for inp in TEST_INPUTS:
            r = classify_reply(inp)
            print(f"{inp[:39]:<40} {r['stage']:<10} {r['intent']:<10} "
                  f"{r['confidence']:<6.2f} {r['reason'][:50]}")
    else:
        app = create_app()
        print(f"WattsEye WhatsApp webhook listening on http://{args.host}:{args.port}/webhook/whatsapp")
        print("Expose via: ngrok http 8080  (set the https URL as the Meta webhook Callback URL,")
        print("            verify token = $META_VERIFY_TOKEN, then subscribe to the 'messages' field)")
        app.run(host=args.host, port=args.port)

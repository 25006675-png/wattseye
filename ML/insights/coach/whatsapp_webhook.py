"""Flask webhook endpoint that receives Twilio WhatsApp replies.

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

Deploy:
  - Run on the Pi on port 8080
  - Expose via ngrok (`ngrok http 8080`)
  - Paste the public URL into Twilio Console → Messaging → Sandbox settings
    → "When a message comes in" → `https://<your-host>/webhook/whatsapp`
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

# Reuse the dotenv loader from whatsapp.py so we get GEMINI_API_KEY etc.
from .whatsapp import _load_dotenv  # noqa: F401 — import side-effect loads .env

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


# ---------- TwiML ----------

def _xml_escape(text: str) -> str:
    """Escape XML special chars and strip any non-ASCII that may upset Twilio's parser."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;"))


def twiml_reply(text: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Message>{_xml_escape(text)}</Message></Response>')


# ---------- Flask app ----------

def create_app():
    if Flask is None:
        raise RuntimeError("flask not installed. pip install flask")

    app = Flask(__name__)

    @app.route("/webhook/whatsapp", methods=["POST"])
    def whatsapp_webhook():
        body = request.form.get("Body", "")
        from_number = request.form.get("From", "")
        log.info("whatsapp reply from=%s body=%r", from_number, body)

        archetype = _most_recent_pushed_archetype()
        classification = classify_reply(body)
        log.info("classified intent=%s conf=%.2f stage=%s reason=%r",
                 classification["intent"], classification["confidence"],
                 classification["stage"], classification.get("reason", ""))

        record_user_action(archetype or "unknown", classification, body, from_number)
        return Response(twiml_reply(compose_ack(classification)), mimetype="text/xml")

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
        print("Expose via: ngrok http 8080  (paste the https URL into Twilio sandbox settings)")
        app.run(host=args.host, port=args.port)

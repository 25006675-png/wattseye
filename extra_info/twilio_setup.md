# === Terminal 1 — Webhook (Flask) ===
  cd C:\Users\user\wattseye
  python -m ML.insights.coach.whatsapp_webhook --port 8080


  # === Terminal 2 — Ngrok tunnel ===
  ngrok http 8080
  # Copy the printed https://<random>.ngrok-free.app URL


  # === Browser — Twilio Sandbox Configuration (manual, one-time per ngrok session) ===
  # https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn
  # "When a message comes in" → https://<random>.ngrok-free.app/webhook/whatsapp
  # Method: POST → Save


  # === Terminal 3 — Send a test message (optional, to fire a card) ===
  cd C:\Users\user\wattseye
  python -m ML.insights.coach.whatsapp --send
  # Phone receives message; reply YES / NO / LATER; check terminal 1 for log

  Keep terminals 1 and 2 open the whole session. Don't touch terminal 3 once you've tested — it has a 12h per-archetype
  rate limit anyway.

  If WhatsApp sandbox expired (silent send, no message arrives): re-join from your phone — send join wealth-earn to +1 415
  523 8886.

  To verify the round trip after replying:
  type ML\insights\coach\_user_actions.json

  That's the whole loop. Memorise the four lines and you're set.
  
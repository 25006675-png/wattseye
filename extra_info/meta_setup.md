# WhatsApp via Meta Cloud API — run sheet

Replaces the old Twilio sandbox. Credentials live in `.env` (gitignored).

## Open the 24h window first (every demo session)
Free-form alerts only deliver if the recipient messaged the number within the
last 24h. From the phone (+60195613440), send any text ("hi") to the Meta test
number (+1 555 657 9418). That opens the window for 24h.

> Before the window is open you can still prove wiring with the pre-approved
> template:
> ```
> python -m ML.insights.coach.whatsapp --hello
> ```
> A `hello_world` message lands on the phone; templates bypass the 24h window.

## === Terminal 1 — Webhook (Flask) ===
```
cd C:\Users\user\wattseye
python -m ML.insights.coach.whatsapp_webhook --port 8080
```

## === Terminal 2 — Ngrok tunnel ===
```
ngrok http 8080
```
Copy the printed `https://<random>.ngrok-free.app` URL.

## === Browser — Meta webhook config (one-time per ngrok session) ===
developers.facebook.com → your app → WhatsApp → Configuration → Webhook:
- Callback URL: `https://<random>.ngrok-free.app/webhook/whatsapp`
- Verify token: must equal `META_VERIFY_TOKEN` in `.env` (`wattseye_verify_2026`)
- Click **Verify and save** (Meta hits the GET handshake), then **Subscribe**
  to the `messages` field.

## === Terminal 3 — Send a test card (optional) ===
```
cd C:\Users\user\wattseye
python -m ML.insights.coach.whatsapp --send
```
Phone receives the message; reply YES / NO / LATER; check terminal 1 for the
log and the ack that gets POSTed back.

Keep terminals 1 and 2 open the whole session. Terminal 3 has a 12h
per-archetype rate limit anyway.

## Verify the round trip after replying
```
type ML\insights\coach\_user_actions.json
```

## Token note
`META_ACCESS_TOKEN` is the temporary 24h token. For a token that doesn't
expire: Business Settings → System Users → create one with WhatsApp
permissions → generate a permanent token, then swap it into `.env`.

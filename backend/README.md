# WattsEye Backend Bridge

This starts the local HTTP API consumed by the Flutter app.

```powershell
python backend/api_server.py
```

Default URL:

```text
http://localhost:8080
```

Implemented endpoints:

- `GET /api/dashboard`
- `GET /api/coach/cards`
- `POST /api/coach/cards/{archetype_key}/action`
- `GET /api/whatsapp/status`
- `POST /api/whatsapp/send`
- `GET /api/bill`
- `GET /api/history`

The bridge currently uses the existing demo snapshot and coach engine from
`ML/insights/coach/coach_engine.py`. Replace `dashboard_payload()` with live Pi
sensor/database data when the hardware pipeline is ready; keep the JSON keys the
same so the Flutter app continues to work.

Run Flutter against another backend host:

```powershell
flutter run --dart-define=WATTSEYE_API_BASE=http://192.168.1.50:8080
```

For Android emulator use `http://10.0.2.2:8080` instead of `localhost`.

## WhatsApp

The Flutter dashboard's WhatsApp button calls:

```text
POST /api/whatsapp/send
```

Body:

```json
{"archetype_key": "left_on_empty"}
```

For real sending, create `.env` in the repo root with:

```text
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+60xxxxxxxxx
```

Then restart `python backend/api_server.py`.

To test message rendering without sending:

```powershell
Invoke-RestMethod -Uri http://localhost:8080/api/whatsapp/send `
  -Method Post `
  -ContentType application/json `
  -Body '{"archetype_key":"left_on_empty","dry_run":true}'
```

For reply handling, run the Twilio webhook separately:

```powershell
python -m ML.insights.coach.whatsapp_webhook --port 8081
ngrok http 8081
```

Set the Twilio Sandbox incoming-message webhook to:

```text
https://<ngrok-host>/webhook/whatsapp
```

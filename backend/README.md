# WattsEye Backend Bridge

This starts the local HTTP API consumed by the Flutter app.

```powershell
python backend/api_server.py
```

Install backend dependencies first if PDF or ML endpoints report missing
packages:

```powershell
python -m pip install -r backend/requirements.txt
```

Default URL:

```text
http://localhost:8080
```

Implemented endpoints:

- `GET /api/dashboard`
- `GET /api/coach/cards`
- `POST /api/coach/cards/{archetype_key}/action`
- `GET /api/integrations/status`
- `GET /api/weather?city=Kuala%20Lumpur`
- `GET /api/ml/status`
- `POST /api/ml/nilm/infer`
- `GET /api/report/monthly?mode=summary`
- `GET /api/whatsapp/status`
- `POST /api/whatsapp/send`
- `GET /api/bill`
- `GET /api/history`

The bridge currently uses the existing demo snapshot and coach engine from
`ML/insights/coach/coach_engine.py`. Replace `dashboard_payload()` with live Pi
sensor/database data when the hardware pipeline is ready; keep the JSON keys the
same so the Flutter app continues to work.

## PDF, Weather, And ML

The Profile tab reads:

```text
GET /api/integrations/status
```

This reports whether PDF generation, Open-Meteo weather, NILM `.pth` models,
PyTorch, and `.joblib` models are available.

Generate a monthly PDF:

```powershell
Invoke-WebRequest -Uri "http://localhost:8080/api/report/monthly?mode=detailed" `
  -OutFile wattseye_report_detailed.pdf
```

Fetch weather:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/weather?city=Kuala%20Lumpur"
```

Check ML model files/runtime:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/ml/status"
```

Run NILM inference on a synthetic 240-sample window:

```powershell
Invoke-RestMethod -Uri "http://localhost:8080/api/ml/nilm/infer" `
  -Method Post `
  -ContentType application/json `
  -Body '{"models":"all"}'
```

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

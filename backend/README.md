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
- `GET /api/phones`
- `POST /api/phones/pair`
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

## Connect A New Phone

Use this flow when the backend is running on the Raspberry Pi or your laptop.
The phone and backend must be on the same WiFi network.

1. Start the backend:

```powershell
cd wattseye_repo
python backend/api_server.py --host 0.0.0.0 --port 8080
```

2. Find the backend computer's local IP address:

```powershell
ipconfig
```

Use the `IPv4 Address`, for example `192.168.1.50`.

3. Run or build the Flutter app for the phone with that backend address:

```powershell
cd wattseye_app
flutter run --dart-define=WATTSEYE_API_BASE=http://192.168.1.50:8080
```

4. Open WattsEye on the phone, then go to `Profile`.
5. Confirm `API bridge` says `Connected`.
6. Read the `Pairing code` shown under `Connected phones`.
7. Tap `Pair this phone`.
8. Enter a phone name and the 6-digit pairing code.
9. Tap `Connect phone`.
10. Pull down to refresh Profile. The phone should appear in `Connected phones`.

You can also verify pairing from PowerShell:

```powershell
Invoke-RestMethod -Uri http://192.168.1.50:8080/api/phones
```

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

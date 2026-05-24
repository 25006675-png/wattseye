# WattsEye App

Flutter frontend for the WattsEye dashboard.

## Run On A New Phone

1. Start the backend from the repo root:

```powershell
cd ..\backend
python api_server.py --host 0.0.0.0 --port 8080
```

2. Find the backend computer's WiFi IP:

```powershell
ipconfig
```

3. Connect the phone to the same WiFi.
4. Run the app using the backend IP:

```powershell
flutter run --dart-define=WATTSEYE_API_BASE=http://192.168.1.50:8080
```

Replace `192.168.1.50` with your real IPv4 address.

5. Open `Profile`.
6. Check `API bridge` is `Connected`.
7. Copy the `Pairing code` shown in `Connected phones`.
8. Tap `Pair this phone`.
9. Enter the phone name and 6-digit pairing code.
10. Tap `Connect phone`.

After pairing, pull down on Profile to refresh. The phone appears in the
connected phone list.

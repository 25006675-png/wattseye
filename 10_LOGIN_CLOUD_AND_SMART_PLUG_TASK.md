# 10 - Login, Cloud, and Smart Plug Task

## 1. Purpose of this file

This file describes the task scope for the login, cloud sync, and smart plug part of WattsEye.

The goal is to let a user enter the app, select or identify a home/device, and clearly understand whether the dashboard is showing live local data, synced cloud history, cached history, or demo/sample data.

Core rule:

```text
Login first.
Live local monitoring second.
Cloud sync third.
Remote access fourth.
```

## 2. Required architecture

WattsEye should use a login-first, local-first architecture.

```text
Best case:
Login + internet + cloud
-> user login
-> remote dashboard history
-> Supabase sync

Normal case:
Login + home WiFi
-> phone/laptop opens Raspberry Pi dashboard locally
-> Pi reads sensors, runs AI, stores history, and controls ESP32

Fallback case:
Login + Pi hotspot mode
-> user connects directly to the Pi WiFi
-> dashboard, local database, AI, MQTT, and IR cutoff still work offline
```

This architecture keeps the product usable when internet access is unstable.

Important distinction:

```text
Login means the user can enter the app.
It does not guarantee the displayed data is live from the home.
```

If the user is not connected to the home Pi, the dashboard may show cloud-synced history, cached history, or demo/sample data. The UI must label this clearly.

## 3. Cloud responsibilities

Cloud should handle:

- User login/register/logout
- Synced history across devices
- Backup of selected readings
- Remote dashboard access, if enabled
- User/device ownership mapping

Cloud should not handle:

- Real-time sensor reading
- Core NILM inference
- MQTT control between Pi and ESP32
- AC cutoff command path
- Local dashboard availability

## 4. Login task scope

Split login work between frontend UI and backend/auth setup.

Frontend-owned UI:

1. Login page
2. Register page
3. Logout button
4. Redirect to dashboard after login
5. Clear data source label after login

Backend/cloud-owned setup:

1. Define required auth fields and auth states
2. Provide local/demo auth mode if Supabase Auth is not ready
3. Configure Supabase Auth after the local login flow works
4. Expose the selected home/device state needed by the dashboard

The dashboard should not pretend every logged-in session is live. After login, it should show one of these states:

```text
Live from home Pi
Synced from cloud
Cached local history
Demo/sample data
```

## 5. Supabase table task

Minimum table:

```sql
create table energy_readings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  device_id text not null,
  timestamp timestamptz not null,
  power_watts numeric not null,
  source text not null default 'ct_clamp',
  synced boolean not null default true,
  created_at timestamptz not null default now()
);
```

Better prototype table:

```sql
create table energy_readings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid,
  device_id text not null,
  timestamp timestamptz not null,
  total_power_watts numeric,
  ac_power_watts numeric,
  residual_power_watts numeric,
  appliance_name text,
  power_watts numeric,
  source text not null,
  synced boolean not null default true,
  created_at timestamptz not null default now()
);
```

Suggested `source` values:

```text
ct_clamp
nilm_prediction
smart_plug
manual_test
```

## 6. Offline-first sync task

The Pi should write every reading locally first.

```text
New reading on the Pi
-> save to local database
-> mark synced = false
-> if internet and user login exist, upload to Supabase
-> mark local row synced = true after upload succeeds
```

If internet is unavailable:

```text
Keep reading locally.
Keep dashboard running.
Try sync again later.
```

The dashboard can show:

```text
Local device: Online
Data source: Live from home Pi
Cloud sync: Paused
Pending readings: 248
```

Remote-only example:

```text
Local device: Not reachable
Data source: Synced cloud history
Last synced: 12 minutes ago
```

## 7. Smart plug task

Smart plugs provide exact readings for selected plug-in appliances.

Good uses:

- Fridge validation
- Lamp or fan exact reading
- Computer setup monitoring
- Comparing NILM estimate against a known plug load

Bad uses:

- Replacing the main clamp
- Measuring hardwired AC
- Depending on smart plugs for the final demo

Recommended local data path:

```text
Smart plug
-> WiFi / local API / MQTT
-> Raspberry Pi
-> local database
-> dashboard
-> Supabase sync when available
```

Suggested local payload:

```json
{
  "device_id": "plug-fridge-01",
  "appliance_name": "Fridge",
  "power_watts": 118,
  "energy_wh": 640,
  "online": true,
  "timestamp": "2026-05-18T20:30:00+08:00",
  "source": "smart_plug"
}
```

## 8. Assignment message

Suggested assignment message:

```text
Can you take the login, cloud sync, and smart plug task?
The core system will still run locally, but your part will let users enter the app and clearly see whether the data is live, synced, cached, or demo data.
```

Deliverables:

1. Login/auth flow contract for frontend
2. Local/demo auth first, then Supabase Auth if ready
3. Data source state after login
4. `energy_readings` table structure
5. One manually inserted test reading
6. Short screenshots or demo by the early checkpoint
7. This task guide kept updated

Do not assign this person ownership of:

- Raspberry Pi sensor data collection
- Core CT sensor logic
- Main dashboard live pipeline
- MQTT architecture
- Offline queue reliability
- Final demo integration

## 9. Completion target

Successful completion means the app can show this flow:

```text
Login -> selected home/device -> data source status -> synced history -> smart plug readings -> remote access story
```

The work must stay separated from the core sensing/control loop:

```text
Two CT clamps -> local Pi dashboard -> NILM -> occupancy alert -> IR cutoff
```

This keeps responsibilities clear while still making the login/cloud/smart plug task useful for the final product story.

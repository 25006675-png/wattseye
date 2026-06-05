#!/bin/bash
# Full demo bring-up: reader + api + bridge with demo thresholds, plus the rule.
# Defaults: auto_off (fan cuts by itself at ~10s empty) + Gemini WhatsApp confirm.
#   RULE_MODE=remind            -> alert + wait for YES reply (the ngrok/webhook flow)
#   WATTSEYE_HIGH_POWER_WATTS=N -> "AC on" threshold (demo default: 3W)
cd ~/wattseye || exit 1
source .venv/bin/activate

export WATTSEYE_NILM=1
export WATTSEYE_NILM_GAIN=1.5
export WATTSEYE_HIGH_POWER_WATTS="${WATTSEYE_HIGH_POWER_WATTS:-3}"
export WATTSEYE_EMPTY_ROOM_MINUTES=0.1
export WATTSEYE_RULE_MIN_MINUTES=0.1
export WATTSEYE_LEFT_ON_MIN_DURATION_MIN=0.1667
export WATTSEYE_LEFT_ON_MIN_POWER_W="$WATTSEYE_HIGH_POWER_WATTS"

cat > backend/_smart_rule.json <<JSON
{"enabled": true, "empty_minutes": 0.1667, "mode": "${RULE_MODE:-auto_off}"}
JSON
rm -f ML/insights/coach/_whatsapp_sent.json backend/reminders.json

pkill -f ads1115_reader 2>/dev/null
pkill -f 'api_server.py' 2>/dev/null
pkill -f 'backend.pi_bridge' 2>/dev/null
sleep 1

nohup setsid python -m ML.sensing.ads1115_reader      > /tmp/reader.log 2>&1 </dev/null & disown
nohup setsid python backend/api_server.py             > /tmp/api.log    2>&1 </dev/null & disown
nohup setsid python -u -m backend.pi_bridge           > /tmp/pi_bridge.log 2>&1 </dev/null & disown
sleep 10

echo "=== processes ==="
ps -eo pid,args | awk '$2=="python" && (/ads1115/||/api_server/||/pi_bridge/||/whatsapp_webhook/){print $1, $4, $5}'
echo "=== rule (mode + 10s) ==="; cat backend/_smart_rule.json; echo
echo "=== power now (turn the FAN ON; ac_watts must exceed HIGH_POWER=$WATTSEYE_HIGH_POWER_WATTS) ==="
timeout 3 mosquitto_sub -h 127.0.0.1 -t wattseye/power -v | tail -1
echo "=== api live? ==="; curl -s -m 4 http://localhost:8080/api/dashboard | head -c 70

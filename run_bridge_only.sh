#!/bin/bash
# Restart ONLY the bridge with demo thresholds.
# Leaves reader / api / webhook / app untouched.
cd ~/wattseye || exit 1
source .venv/bin/activate
export WATTSEYE_NILM=1
export WATTSEYE_NILM_GAIN=1.5
export WATTSEYE_HIGH_POWER_WATTS=3
export WATTSEYE_EMPTY_ROOM_MINUTES=0.1
export WATTSEYE_RULE_MIN_MINUTES=0.1
export WATTSEYE_LEFT_ON_MIN_DURATION_MIN=0.1667
export WATTSEYE_LEFT_ON_MIN_POWER_W="$WATTSEYE_HIGH_POWER_WATTS"

cat > backend/_smart_rule.json <<JSON
{"enabled": true, "empty_minutes": 0.1667, "mode": "${RULE_MODE:-auto_off}"}
JSON

pkill -f 'backend.pi_bridge' 2>/dev/null
sleep 1
nohup setsid python -u -m backend.pi_bridge > /tmp/pi_bridge.log 2>&1 </dev/null & disown
sleep 9
echo "=== bridge pid ==="; ps -eo pid,args | awk '$2=="python" && /pi_bridge/{print $1}'
head -2 /tmp/pi_bridge.log
echo "=== rule ==="; cat backend/_smart_rule.json

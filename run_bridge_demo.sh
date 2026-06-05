#!/bin/bash
# Demo launcher for the AC smart-rule (auto-off + Gemini WhatsApp).
# HIGH_POWER_WATTS is overridable: use a low value (e.g. 3) to test without a
# fan; use ~15-20 for the real demo so idle noise doesn't trigger it.
cd ~/wattseye || exit 1
source .venv/bin/activate

# Demo rule: auto-off after ~10 seconds empty (0.1667 min).
cat > backend/_smart_rule.json <<'JSON'
{"enabled": true, "empty_minutes": 0.1667, "mode": "auto_off"}
JSON

# Stop any running bridge (by PID, never pkill -f which can self-kill the shell).
kill $(ps -eo pid,args | awk '$2=="python" && /pi_bridge/{print $1}') 2>/dev/null
sleep 1

export WATTSEYE_NILM=1
export WATTSEYE_NILM_GAIN=1.5
export WATTSEYE_HIGH_POWER_WATTS="${WATTSEYE_HIGH_POWER_WATTS:-15}"
export WATTSEYE_EMPTY_ROOM_MINUTES=0.1
export WATTSEYE_RULE_MIN_MINUTES=0.1

nohup setsid python -u -m backend.pi_bridge > /tmp/pi_bridge.log 2>&1 </dev/null &
disown
sleep 9
echo "=== launched (HIGH_POWER_WATTS=$WATTSEYE_HIGH_POWER_WATTS, rule=10s/auto_off) ==="
head -3 /tmp/pi_bridge.log
ps -eo pid,args | awk '$2=="python" && /pi_bridge/{print "bridge pid", $1, "OK"}'

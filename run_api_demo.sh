#!/bin/bash
# Restart ONLY the API with demo thresholds for live Coach cards.
cd ~/wattseye || exit 1
source .venv/bin/activate

export WATTSEYE_HIGH_POWER_WATTS=3
export WATTSEYE_EMPTY_ROOM_MINUTES=0.1
export WATTSEYE_RULE_MIN_MINUTES=0.1
export WATTSEYE_LEFT_ON_MIN_DURATION_MIN=0.1667
export WATTSEYE_LEFT_ON_MIN_POWER_W=3

python -m py_compile ML/insights/coach/correlator.py ML/insights/coach/templates.py
pkill -f 'api_server.py' 2>/dev/null
sleep 1
nohup setsid python backend/api_server.py > /tmp/api.log 2>&1 </dev/null & disown
sleep 3

echo "=== api pid ==="
pgrep -af 'api_server.py'
echo "=== api rule ==="
curl -s -m 3 http://localhost:8080/api/ac/rule
echo
echo "=== live coach cards ==="
curl -s -m 5 'http://localhost:8080/api/coach/cards?mode=live' \
  | python -m json.tool \
  | grep -E 'archetype_key|headline|impact_text|action_text' \
  | head -24 || true

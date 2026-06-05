#!/bin/bash
# Reply-driven flow: rule alerts -> user replies YES on WhatsApp -> webhook cuts AC.
cd ~/wattseye || exit 1
source .venv/bin/activate

# Rule in REMIND mode: alert at ~10s empty, then wait for the WhatsApp reply.
cat > backend/_smart_rule.json <<'JSON'
{"enabled": true, "empty_minutes": 0.1667, "mode": "remind"}
JSON

# Clear the push rate-limit log so repeated demo alerts aren't suppressed.
rm -f ML/insights/coach/_whatsapp_sent.json

# Restart the webhook on 8081 (8080 is the api_server).
kill $(ps -eo pid,args | awk '$2=="python" && /whatsapp_webhook/{print $1}') 2>/dev/null
sleep 1
nohup setsid python -m ML.insights.coach.whatsapp_webhook --port 8081 > /tmp/webhook.log 2>&1 </dev/null &
disown
sleep 3
echo "=== webhook ==="
ps -eo pid,args | awk '$2=="python" && /whatsapp_webhook/{print "webhook pid", $1, "OK"}'
tail -2 /tmp/webhook.log
echo "=== VERIFY TOKEN (paste THIS into the Meta webhook config) ==="
grep '^META_VERIFY_TOKEN=' .env | cut -d= -f2-
echo "=== rule now ==="
cat backend/_smart_rule.json

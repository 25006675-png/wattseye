#!/bin/bash
mosquitto_pub -h 127.0.0.1 -t wattseye/ac/command \
  -m '{"command":"on","reason":"manual_rearm"}'
sleep 2
timeout 5 mosquitto_sub -h 127.0.0.1 -t wattseye/ac/state -C 1 -v || true

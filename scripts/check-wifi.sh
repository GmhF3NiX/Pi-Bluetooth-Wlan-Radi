#!/bin/bash
sleep 15
SSID=$(iwgetid -r wlan0 2>/dev/null)
if [ -z "$SSID" ]; then
    echo "[check-wifi] Kein WLAN — Starte Hotspot"
    /usr/local/bin/start-hotspot.sh
else
    echo "[check-wifi] Verbunden mit: $SSID"
fi

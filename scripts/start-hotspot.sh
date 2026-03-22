#!/bin/bash
iw dev wlan0 interface add uap0 type __ap 2>/dev/null || true
ip addr flush dev uap0
ip addr add 192.168.4.1/24 dev uap0
ip link set uap0 up
sleep 1
systemctl start hostapd
systemctl start dnsmasq

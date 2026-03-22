#!/bin/bash
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
ip link set uap0 down 2>/dev/null || true
iw dev uap0 del 2>/dev/null || true

# Pi Bluetooth WLAN Radio
### by Olli (GmhF3NiX)

Ein vollständiges Internetradio auf Basis des Raspberry Pi Zero 2W mit:
- Webradio (12 vorinstallierte Sender)
- Spotify Connect (via Raspotify)
- Bluetooth Audio Sink
- Captive Portal WLAN-Setup
- Home Assistant Integration
- Tailscale für Remote-Zugriff

## Installation

curl -sSL https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radi/main/install.sh | sudo bash

Nach Installation: sudo reboot

## Erster Start

Hotspot: Pi-Radio-Setup (kein Passwort)
Browser: http://192.168.4.1
Nach WLAN-Setup erreichbar unter: http://anlage.local

## Erreichbarkeit

Heimnetz:  http://anlage.local
Kein WLAN: http://192.168.4.1 (Hotspot Pi-Radio-Setup)
Fremdes Netz: Tailscale IP

## Spotify Connect auf fremden Netzwerken

Tailscale installieren:
curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up

In /etc/raspotify/conf eintragen:
LIBRESPOT_ZEROCONF_INTERFACE=<Tailscale-IP>
LIBRESPOT_AP_PORT=443

Made with love by Olli

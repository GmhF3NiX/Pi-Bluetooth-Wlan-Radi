#!/bin/bash
# ============================================================
#  PI BLUETOOTH WLAN RADIO — INSTALL SCRIPT
#  Autor: Olli (GmhF3NiX)
#  GitHub: https://github.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radio
#
#  Verwendung:
#  curl -sSL https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radio/main/install.sh | sudo bash
# ============================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${CYAN}[•] $1${NC}"; }
success() { echo -e "${GREEN}[✓] $1${NC}"; }
warn()    { echo -e "${YELLOW}[!] $1${NC}"; }
error()   { echo -e "${RED}[✗] $1${NC}"; exit 1; }

echo ""
echo -e "${RED}=======================================${NC}"
echo -e "${RED}   PI BLUETOOTH WLAN RADIO${NC}"
echo -e "${RED}   by Olli${NC}"
echo -e "${RED}=======================================${NC}"
echo ""

# Root check
if [ "$EUID" -ne 0 ]; then
  error "Bitte als root ausführen: sudo bash install.sh"
fi

# ── Pakete installieren ──────────────────────────────────────
info "Installiere Pakete..."
apt update -qq
apt install -y -qq \
  python3-flask \
  mpg123 \
  bluez \
  bluez-tools \
  bluez-alsa-utils \
  pulseaudio \
  pulseaudio-module-bluetooth \
  avahi-daemon \
  hostapd \
  dnsmasq \
  wireless-tools \
  net-tools
success "Pakete installiert"

# ── Ordner erstellen ─────────────────────────────────────────
info "Erstelle Ordner..."
mkdir -p /opt/radio/templates
mkdir -p /opt/radio/static
mkdir -p /etc/radio
success "Ordner erstellt"

# ── ALSA konfigurieren ───────────────────────────────────────
info "Konfiguriere Audio (USB DAC)..."
cat > /etc/asound.conf << 'EOF'
pcm.!default {
  type hw
  card 0
}
ctl.!default {
  type hw
  card 0
}
EOF
success "Audio konfiguriert"

# ── hostapd konfigurieren ────────────────────────────────────
info "Konfiguriere Hotspot..."
mkdir -p /etc/hostapd
cat > /etc/hostapd/hostapd.conf << 'EOF'
interface=uap0
driver=nl80211
ssid=Pi-Radio-Setup
hw_mode=g
channel=6
auth_algs=1
ignore_broadcast_ssid=0
EOF
echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' > /etc/default/hostapd
systemctl unmask hostapd 2>/dev/null || true
systemctl disable hostapd 2>/dev/null || true
success "Hotspot konfiguriert (SSID: Pi-Radio-Setup)"

# ── dnsmasq konfigurieren ────────────────────────────────────
info "Konfiguriere DHCP/DNS..."
cat > /etc/dnsmasq.d/hotspot.conf << 'EOF'
interface=uap0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
address=/#/192.168.4.1
EOF
systemctl disable dnsmasq 2>/dev/null || true
success "DHCP/DNS konfiguriert"

# ── NetworkManager: uap0 ignorieren ─────────────────────────
info "NetworkManager konfigurieren..."
mkdir -p /etc/NetworkManager/conf.d
cat > /etc/NetworkManager/conf.d/unmanaged.conf << 'EOF'
[keyfile]
unmanaged-devices=interface-name:uap0
EOF
success "uap0 aus NetworkManager ausgeschlossen"

# ── Scripts erstellen ────────────────────────────────────────
info "Erstelle Scripts..."

cat > /usr/local/bin/start-hotspot.sh << 'EOF'
#!/bin/bash
iw dev wlan0 interface add uap0 type __ap 2>/dev/null || true
ip addr flush dev uap0
ip addr add 192.168.4.1/24 dev uap0
ip link set uap0 up
sleep 1
systemctl start hostapd
systemctl start dnsmasq
EOF
chmod +x /usr/local/bin/start-hotspot.sh

cat > /usr/local/bin/stop-hotspot.sh << 'EOF'
#!/bin/bash
systemctl stop hostapd 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
ip link set uap0 down 2>/dev/null || true
iw dev uap0 del 2>/dev/null || true
EOF
chmod +x /usr/local/bin/stop-hotspot.sh

cat > /usr/local/bin/check-wifi.sh << 'EOF'
#!/bin/bash
sleep 15
SSID=$(iwgetid -r wlan0 2>/dev/null)
if [ -z "$SSID" ]; then
    echo "[check-wifi] Kein WLAN — Starte Hotspot"
    /usr/local/bin/start-hotspot.sh
else
    echo "[check-wifi] Verbunden mit: $SSID"
fi
EOF
chmod +x /usr/local/bin/check-wifi.sh

success "Scripts erstellt"

# ── Dateien von GitHub laden ─────────────────────────────────
info "Lade Radio App von GitHub..."

BASE_URL="https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radi/main"

curl -sSL "$BASE_URL/radio.py" -o /opt/radio/radio.py
curl -sSL "$BASE_URL/templates/radio.html" -o /opt/radio/templates/radio.html
curl -sSL "$BASE_URL/templates/setup.html" -o /opt/radio/templates/setup.html
curl -sSL "$BASE_URL/templates/connecting.html" -o /opt/radio/templates/connecting.html

success "Radio App geladen"

# ── Systemd Services ─────────────────────────────────────────
info "Erstelle Systemd Services..."

cat > /etc/systemd/system/uap0.service << 'EOF'
[Unit]
Description=Virtual WiFi AP Interface
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/start-hotspot.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/check-wifi.service << 'EOF'
[Unit]
Description=Check WiFi and start hotspot if needed
After=network.target uap0.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/check-wifi.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/bt-agent.service << 'EOF'
[Unit]
Description=Bluetooth Auto-Pair Agent
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/bin/bash -c 'sleep 5 && rfkill unblock bluetooth && hciconfig hci0 up && bluetoothctl power on && bluetoothctl discoverable on && bluetoothctl pairable on && bt-agent -c NoInputNoOutput'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/radio.service << 'EOF'
[Unit]
Description=Pi Bluetooth WLAN Radio by Olli
After=network.target sound.target uap0.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/radio
ExecStart=/usr/bin/python3 /opt/radio/radio.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable uap0
systemctl enable check-wifi
systemctl enable bt-agent
systemctl enable radio
success "Services erstellt und aktiviert"

# ── Fertig ───────────────────────────────────────────────────
echo ""
echo -e "${RED}=======================================${NC}"
echo -e "${GREEN}   INSTALLATION ABGESCHLOSSEN!${NC}"
echo -e "${RED}=======================================${NC}"
echo ""
echo -e "  ${CYAN}Jetzt neu starten:${NC}"
echo -e "  ${RED}sudo reboot${NC}"
echo ""
echo -e "  ${CYAN}Nach dem Neustart:${NC}"
echo -e "  Hotspot: ${RED}Pi-Radio-Setup${NC}"
echo -e "  Web:     ${RED}http://anlage.local${NC}"
echo ""
echo -e "  ${CYAN}Made with ❤️  by Olli${NC}"
echo ""

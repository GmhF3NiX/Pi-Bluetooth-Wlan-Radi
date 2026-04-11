#!/usr/bin/env python3
"""
====================================================
  PI ZERO 2W RADIO
  Captive Portal → WLAN Setup → Webradio Interface
====================================================
"""

import os, json, subprocess, threading, time, logging
from flask import Flask, render_template, request, redirect, jsonify, send_from_directory

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("radio")

CONFIG_FILE = "/etc/radio/config.json"
STATIONS_FILE = "/etc/radio/stations.json"

# ── Standard Sender ──────────────────────────────
DEFAULT_STATIONS = [
    {"name": "SWR3",            "url": "http://swr-swr3-live.cast.addradio.de/swr/swr3/live/mp3/128/stream.mp3", "genre": "Pop"},
    {"name": "WDR 2",           "url": "http://wdr-wdr2-aachenundregion.icecastssl.wdr.de/wdr/wdr2/aachenundregion/mp3/128/stream.mp3", "genre": "Pop"},
    {"name": "Bayern 3",        "url": "http://dispatcher.rndfnk.com/br/br3/live/mp3/low", "genre": "Pop"},
    {"name": "NDR 2",           "url": "http://ndr-ndr2-live.cast.addradio.de/ndr/ndr2/live/mp3/128/stream.mp3", "genre": "Pop"},
    {"name": "1LIVE",           "url": "http://wdr-1live-live.cast.addradio.de/wdr/1live/live/mp3/128/stream.mp3", "genre": "Pop"},
    {"name": "Deutschlandfunk", "url": "http://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3", "genre": "News"},
    {"name": "Radio Bob",       "url": "http://stream.radiobob.de/bob-live/mp3-128/mediaplayer", "genre": "Rock"},
    {"name": "Rock Antenne",    "url": "http://www.rockantenne.de/static/live/rockantenne/mp3/high.m3u", "genre": "Rock"},
    {"name": "Jazz Radio",      "url": "http://jazz.stream.laut.fm/jazz", "genre": "Jazz"},
    {"name": "Klassik Radio",   "url": "http://stream.klassikradio.de/live/mp3-192/stream.klassikradio.de/", "genre": "Klassik"},
    {"name": "Energy Berlin",   "url": "http://energyradio.de/berlin", "genre": "Electronic"},
    {"name": "sunshine live",   "url": "http://stream.sunshine-live.de/live/mp3-192", "genre": "Electronic"},
]

# ── Aktueller Status ─────────────────────────────
state = {
    "playing": False,
    "station": None,
    "volume": 80,
    "mpg_process": None,
    "bt_mode": False,
    "spotify_mode": False,
}

# ── Config Helpers ───────────────────────────────
def load_config():
    os.makedirs("/etc/radio", exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(data):
    os.makedirs("/etc/radio", exist_ok=True)
    cfg = load_config()
    cfg.update(data)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_stations():
    if os.path.exists(STATIONS_FILE):
        with open(STATIONS_FILE) as f:
            return json.load(f)
    # Defaults speichern
    os.makedirs("/etc/radio", exist_ok=True)
    with open(STATIONS_FILE, "w") as f:
        json.dump(DEFAULT_STATIONS, f, indent=2)
    return DEFAULT_STATIONS

def save_stations(stations):
    with open(STATIONS_FILE, "w") as f:
        json.dump(stations, f, indent=2)

# ── Audio Steuerung ──────────────────────────────
def stop_audio():
    if state["mpg_process"] and state["mpg_process"].poll() is None:
        state["mpg_process"].terminate()
        state["mpg_process"] = None
    state["playing"] = False
    # Auch mpg123 per killall stoppen
    subprocess.run(["killall", "-q", "mpg123"], capture_output=True)

def play_station(url):
    stop_audio()
    time.sleep(0.3)
    try:
        proc = subprocess.Popen(
            ["mpg123", "-q", "--no-control", "--scale", "32768", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        state["mpg_process"] = proc
        state["playing"] = True
        log.info(f"Playing: {url}")
    except Exception as e:
        log.error(f"Playback error: {e}")

def set_volume(vol):
    vol = max(0, min(100, int(vol)))
    state["volume"] = vol
    subprocess.run(["amixer", "-D", "hw:0", "sset", "Speaker", f"{vol}%"], capture_output=True)
    # mpg123 Prozess neu starten wenn läuft (übernimmt neue Lautstärke)
    if state["playing"] and state["station"] is not None:
        stations = load_stations()
        url = stations[state["station"]]["url"]
        threading.Thread(target=play_station, args=(url,), daemon=True).start()

# ── WLAN Scan ────────────────────────────────────
def scan_wifi():
    try:
        result = subprocess.run(
            ["sudo", "iwlist", "wlan0", "scan"],
            capture_output=True, text=True, timeout=10
        )
        networks = []
        seen = set()
        for line in result.stdout.split("\n"):
            line = line.strip()
            if "ESSID:" in line:
                ssid = line.split('"')[1] if '"' in line else ""
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append(ssid)
        return networks
    except Exception as e:
        log.error(f"WiFi scan error: {e}")
        return []

# ── WLAN verbinden ───────────────────────────────
def connect_wifi(ssid, password):
    wpa = f"""ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=DE

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
"""
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as f:
        f.write(wpa)

    subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], capture_output=True)
    time.sleep(5)

    # IP check
    for _ in range(12):
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
        ips = result.stdout.strip().split()
        # Nur echte IPs (nicht AP IP 192.168.4.x)
        real = [ip for ip in ips if not ip.startswith("192.168.4.")]
        if real:
            save_config({"ssid": ssid, "password": password, "connected": True})
            return True
        time.sleep(2)
    return False

# ── AP Modus ─────────────────────────────────────
def is_ap_mode():
    cfg = load_config()
    return not cfg.get("connected", False)

# ── Bluetooth ────────────────────────────────────
def start_bluetooth():
    stop_audio()
    stop_spotify()
    subprocess.run(["sudo", "systemctl", "start", "bluetooth"], capture_output=True)
    subprocess.run(["sudo", "bluetoothctl", "discoverable", "on"], capture_output=True)
    subprocess.run(["sudo", "bluetoothctl", "pairable", "on"], capture_output=True)
    state["bt_mode"] = True
    log.info("Bluetooth A2DP Sink aktiv")

def stop_bluetooth():
    subprocess.run(["sudo", "bluetoothctl", "discoverable", "off"], capture_output=True)
    state["bt_mode"] = False

# ── Spotify ──────────────────────────────────────
def start_spotify():
    stop_audio()
    stop_bluetooth()
    subprocess.run(["sudo", "systemctl", "start", "raspotify"], capture_output=True)
    state["spotify_mode"] = True
    log.info("Spotify Connect aktiv")

def stop_spotify():
    subprocess.run(["sudo", "systemctl", "stop", "raspotify"], capture_output=True)
    state["spotify_mode"] = False

# ════════════════════════════════════════════════
#  ROUTES — CAPTIVE PORTAL (AP Modus)
# ════════════════════════════════════════════════

@app.route("/generate_204")
@app.route("/hotspot-detect.html")
@app.route("/connecttest.txt")
@app.route("/ncsi.txt")
@app.route("/fwlink")
def captive_redirect():
    return redirect("http://192.168.4.1/setup", code=302)

@app.route("/setup")
def setup_page():
    networks = scan_wifi()
    error = request.args.get("error", "")
    return render_template("setup.html", networks=networks, error=error)

@app.route("/setup/connect", methods=["POST"])
def setup_connect():
    ssid = request.form.get("ssid", "").strip()
    password = request.form.get("password", "").strip()

    if not ssid:
        return redirect("/setup?error=Bitte+ein+Netzwerk+wählen")

    return render_template("connecting.html", ssid=ssid)

@app.route("/setup/do_connect", methods=["POST"])
def do_connect():
    ssid = request.form.get("ssid", "")
    password = request.form.get("password", "")

    def connect_async():
        success = connect_wifi(ssid, password)
        if success:
            # AP deaktivieren nach kurzer Verzögerung
            time.sleep(3)
            subprocess.run(["sudo", "systemctl", "stop", "hostapd"], capture_output=True)
            subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"], capture_output=True)

    threading.Thread(target=connect_async, daemon=True).start()
    return jsonify({"status": "connecting"})

@app.route("/setup/status")
def setup_status():
    result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
    ips = result.stdout.strip().split()
    real = [ip for ip in ips if not ip.startswith("192.168.4.") and ip]
    if real:
        return jsonify({"connected": True, "ip": real[0]})
    return jsonify({"connected": False})

@app.route("/setup/reset")
def setup_reset():
    save_config({"connected": False, "ssid": "", "password": ""})
    # wpa_supplicant zurücksetzen
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as f:
        f.write("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\nupdate_config=1\ncountry=DE\n")
    subprocess.run(["sudo", "reboot"], capture_output=True)
    return "Restarting..."

# ════════════════════════════════════════════════
#  ROUTES — RADIO INTERFACE
# ════════════════════════════════════════════════

@app.route("/")
def index():
    stations = load_stations()
    cfg = load_config()
    return render_template("radio.html",
                           stations=stations,
                           state=state,
                           ssid=cfg.get("ssid", ""))

@app.route("/play/<int:station_id>")
def play(station_id):
    stations = load_stations()
    if 0 <= station_id < len(stations):
        s = stations[station_id]
        state["station"] = station_id
        threading.Thread(target=play_station, args=(s["url"],), daemon=True).start()
        return jsonify({"status": "playing", "station": s["name"]})
    return jsonify({"status": "error"}), 404

@app.route("/stop")
def stop():
    stop_audio()
    return jsonify({"status": "stopped"})

@app.route("/volume/<int:vol>")
def volume(vol):
    set_volume(vol)
    return jsonify({"status": "ok", "volume": state["volume"]})

@app.route("/status")
def status():
    stations = load_stations()
    name = stations[state["station"]]["name"] if state["station"] is not None and state["playing"] else "—"
    return jsonify({
        "playing": state["playing"],
        "station": state["station"],
        "station_name": name,
        "volume": state["volume"],
        "bt_mode": state["bt_mode"],
        "spotify_mode": state["spotify_mode"],
    })

@app.route("/bluetooth/on")
def bt_on():
    threading.Thread(target=start_bluetooth, daemon=True).start()
    return jsonify({"status": "bt_on"})

@app.route("/bluetooth/off")
def bt_off():
    stop_bluetooth()
    return jsonify({"status": "bt_off"})

@app.route("/spotify/on")
def spotify_on():
    threading.Thread(target=start_spotify, daemon=True).start()
    return jsonify({"status": "spotify_on"})

@app.route("/spotify/off")
def spotify_off():
    stop_spotify()
    return jsonify({"status": "spotify_off"})

# Sender verwalten
@app.route("/stations")
def get_stations():
    return jsonify(load_stations())

@app.route("/stations/add", methods=["POST"])
def add_station():
    data = request.json
    stations = load_stations()
    stations.append({"name": data["name"], "url": data["url"], "genre": data.get("genre", "")})
    save_stations(stations)
    return jsonify({"status": "ok", "count": len(stations)})

@app.route("/stations/delete/<int:idx>", methods=["DELETE"])
def delete_station(idx):
    stations = load_stations()
    if 0 <= idx < len(stations):
        stations.pop(idx)
        save_stations(stations)
    return jsonify({"status": "ok"})

@app.route("/reboot")
def reboot():
    threading.Thread(target=lambda: (time.sleep(1), subprocess.run(["sudo", "reboot"])), daemon=True).start()
    return jsonify({"status": "rebooting"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)

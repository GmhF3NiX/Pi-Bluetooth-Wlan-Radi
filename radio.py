#!/usr/bin/env python3
"""
Pi Bluetooth WLAN Radio
Autor: Olli (GmhF3NiX)
GitHub: https://github.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radio
"""
import os, json, subprocess, threading, time, logging
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("radio")

STATIONS_FILE = "/etc/radio/stations.json"

DEFAULT_STATIONS = [
    {"name": "1LIVE",            "url": "http://wdr-1live-live.icecast.wdr.de/wdr/1live/live/mp3/128/stream.mp3",                         "genre": "Pop"},
    {"name": "WDR 2",            "url": "http://wdr-wdr2-aachenundregion.icecastssl.wdr.de/wdr/wdr2/aachenundregion/mp3/128/stream.mp3",   "genre": "Pop"},
    {"name": "Bayern 3",         "url": "http://dispatcher.rndfnk.com/br/br3/live/mp3/low",                                               "genre": "Pop"},
    {"name": "NDR 2",            "url": "http://ndr-ndr2-live.cast.addradio.de/ndr/ndr2/live/mp3/128/stream.mp3",                         "genre": "Pop"},
    {"name": "Deutschlandfunk",  "url": "http://st01.sslstream.dlf.de/dlf/01/128/mp3/stream.mp3",                                         "genre": "News"},
    {"name": "sunshine live",    "url": "http://stream.sunshine-live.de/live/mp3-128",                                                    "genre": "Electronic"},
    {"name": "sunshine 90er",    "url": "http://stream.sunshine-live.de/90er/mp3-128",                                                    "genre": "Electronic"},
    {"name": "Jazz Radio",       "url": "http://jazz.stream.laut.fm/jazz",                                                                "genre": "Jazz"},
    {"name": "Klassik Radio",    "url": "http://stream.klassikradio.de/live/mp3-192/stream.klassikradio.de/",                             "genre": "Klassik"},
    {"name": "Radio Bob",        "url": "http://streams.radiobob.de/bob-live/mp3-192/mediaplayer",                                        "genre": "Rock"},
    {"name": "Radio Bob (wollte der Pimmelkopf)", "url": "http://streams.radiobob.de/bob-live/mp3-192/mediaplayer",                       "genre": "Rock"},
]

state = {
    "playing": False,
    "station": None,
    "volume": 80,
    "mpg_process": None,
    "bt_mode": False
}

def load_stations():
    if os.path.exists(STATIONS_FILE):
        with open(STATIONS_FILE) as f:
            return json.load(f)
    os.makedirs("/etc/radio", exist_ok=True)
    with open(STATIONS_FILE, "w") as f:
        json.dump(DEFAULT_STATIONS, f, indent=2)
    return DEFAULT_STATIONS

def save_stations(stations):
    with open(STATIONS_FILE, "w") as f:
        json.dump(stations, f, indent=2)

def stop_audio():
    if state["mpg_process"] and state["mpg_process"].poll() is None:
        state["mpg_process"].terminate()
    state["mpg_process"] = None
    state["playing"] = False
    subprocess.run(["killall", "-q", "mpg123"], capture_output=True)

def play_station(url):
    stop_audio()
    time.sleep(0.3)
    try:
        proc = subprocess.Popen(
            ["mpg123", "-q", "--no-control", "-a", "hw:0,0", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        state["mpg_process"] = proc
        state["playing"] = True
    except Exception as e:
        log.error(f"Playback error: {e}")

def set_volume(vol):
    vol = max(0, min(100, int(vol)))
    state["volume"] = vol
    scaled = int(vol * 37 / 100)
    subprocess.run(["amixer", "-c", "0", "cset", "numid=6", str(scaled)], capture_output=True)
    subprocess.run(["amixer", "-c", "0", "cset", "numid=5", "1"], capture_output=True)

def scan_wifi():
    try:
        result = subprocess.run(["iwlist", "wlan0", "scan"],
                                capture_output=True, text=True, timeout=15)
        networks = []
        seen = set()
        for line in result.stdout.split("\n"):
            if "ESSID:" in line:
                ssid = line.split('"')[1] if '"' in line else ""
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append(ssid)
        return networks
    except Exception as e:
        log.error(f"WiFi scan error: {e}")
        return []

def get_current_ssid():
    try:
        result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
        return result.stdout.strip() or "ONLINE"
    except:
        return "ONLINE"

# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    ssid = get_current_ssid()
    return render_template("radio.html", ssid=ssid)

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
        return redirect("/setup?error=Bitte+Netzwerk+wählen")
    return render_template("connecting.html", ssid=ssid, password=password)

@app.route("/setup/do_connect", methods=["POST"])
def do_connect():
    ssid = request.form.get("ssid", "")
    password = request.form.get("password", "")
    def connect_async():
        try:
            subprocess.run(["nmcli", "dev", "wifi", "connect", ssid,
                          "password", password], capture_output=True, timeout=30)
            time.sleep(5)
            subprocess.run(["/usr/local/bin/stop-hotspot.sh"], capture_output=True)
            time.sleep(3)
            subprocess.run(["systemctl", "stop", "hostapd"], capture_output=True)
            subprocess.run(["systemctl", "stop", "dnsmasq"], capture_output=True)
        except Exception as e:
            log.error(f"Connect error: {e}")
    threading.Thread(target=connect_async, daemon=True).start()
    return jsonify({"status": "connecting"})

@app.route("/setup/status")
def setup_status():
    result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
    ips = [ip for ip in result.stdout.strip().split()
           if not ip.startswith("192.168.4.")]
    if ips:
        return jsonify({"connected": True, "ip": ips[0]})
    return jsonify({"connected": False})

@app.route("/setup/reset")
def setup_reset():
    def do_reset():
        time.sleep(1)
        subprocess.run(["/usr/local/bin/start-hotspot.sh"], capture_output=True)
    threading.Thread(target=do_reset, daemon=True).start()
    return "<html><body style='background:#000;color:#ff0000;font-family:monospace;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center'><div><h2 style=\"font-size:48px;text-shadow:0 0 20px #ff0000\">WLAN RESET</h2><p style='color:#444;margin-top:8px'>Hotspot startet...<br>Suche Pi-Radio-Setup</p></div></body></html>"

# Captive Portal Redirects
@app.route("/generate_204")
@app.route("/generate204")
@app.route("/hotspot-detect.html")
@app.route("/connecttest.txt")
@app.route("/ncsi.txt")
@app.route("/fwlink")
def captive():
    return redirect("http://192.168.4.1/setup", code=302)

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
    name = stations[state["station"]]["name"] if state["station"] is not None else ""
    return jsonify({
        "playing": state["playing"],
        "station": state["station"],
        "station_name": name,
        "volume": state["volume"],
        "bt_mode": state["bt_mode"]
    })

@app.route("/stations")
def get_stations():
    return jsonify(load_stations())

@app.route("/stations/add", methods=["POST"])
def add_station():
    data = request.json
    stations = load_stations()
    stations.append({
        "name": data["name"],
        "url": data["url"],
        "genre": data.get("genre", "")
    })
    save_stations(stations)
    return jsonify({"status": "ok"})

@app.route("/stations/delete/<int:idx>", methods=["DELETE"])
def delete_station(idx):
    stations = load_stations()
    if 0 <= idx < len(stations):
        stations.pop(idx)
        save_stations(stations)
    return jsonify({"status": "ok"})

@app.route("/bluetooth/on")
def bt_on():
    subprocess.run(["bluetoothctl", "discoverable", "on"], capture_output=True)
    subprocess.run(["bluetoothctl", "pairable", "on"], capture_output=True)
    state["bt_mode"] = True
    return jsonify({"status": "bt_on"})

@app.route("/bluetooth/off")
def bt_off():
    subprocess.run(["bluetoothctl", "discoverable", "off"], capture_output=True)
    subprocess.run(["bluetoothctl", "pairable", "off"], capture_output=True)
    subprocess.run(["bluetoothctl", "disconnect"], capture_output=True)
    subprocess.run(["amixer", "-c", "0", "cset", "numid=5", "1"], capture_output=True)
    stop_audio()
    state["bt_mode"] = False
    state["playing"] = False
    return jsonify({"status": "bt_off"})

@app.route("/reboot")
def reboot():
    threading.Thread(
        target=lambda: (time.sleep(1), subprocess.run(["sudo", "reboot"])),
        daemon=True
    ).start()
    return jsonify({"status": "rebooting"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)

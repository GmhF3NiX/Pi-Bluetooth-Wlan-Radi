# 📻 Pi Bluetooth WLAN Radio

**by Olli (GmhF3NiX)**

> Verwandle deinen Raspberry Pi Zero 2W in ein vollwertiges Internetradio mit Weboberfläche, Spotify Connect und Bluetooth — alles über den Browser steuerbar.

![Radio Interface](https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radi/main/screenshots/radio.png)

---

## ✨ Features

| Feature | Beschreibung |
|---------|-------------|
| 📻 Webradio | 12 vorinstallierte Sender, eigene hinzufügbar |
| 🎵 Spotify Connect | Pi als Spotify-Lautsprecher nutzen |
| 🔵 Bluetooth | Handy direkt mit dem Pi verbinden |
| 📶 WLAN Setup | Automatischer Hotspot beim ersten Start |
| 🏠 Home Assistant | Vollständige HA-Integration enthalten |
| 🌐 Tailscale | Spotify Connect auch unterwegs |

---

## 🛒 Hardware

| Teil | Beschreibung | Preis ca. |
|------|-------------|-----------|
| Raspberry Pi Zero 2W | Hauptplatine | ~18€ |
| USB DAC (PCM2704) | Audio-Ausgabe | ~3€ |
| Micro-USB OTG Adapter | Verbindung DAC ↔ Pi | ~1€ |
| MicroSD 16GB | Speicher | ~5€ |

**Verbindung:** USB DAC per OTG an den DATA-Port des Pi → 3,5mm Klinke → AUX IN deiner Anlage

---

## 💿 Betriebssystem vorbereiten

1. **Raspberry Pi Imager** herunterladen: [raspberrypi.com/software](https://www.raspberrypi.com/software/)
2. **Debian 13 Lite (64-bit)** auf MicroSD flashen
3. Im Imager unter *Einstellungen*:
   - SSH aktivieren
   - Benutzername: `olli` / Passwort setzen
4. MicroSD in den Pi einlegen und starten

---

## ⚡ Installation

Per SSH mit dem Pi verbinden und folgenden Befehl ausführen:

```bash
curl -sSL https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radi/main/install.sh | sudo bash
```

Nach der Installation neu starten:

```bash
sudo reboot
```

Das Skript installiert automatisch:
- Flask (Webserver)
- mpg123 (Audioplayback)
- Raspotify (Spotify Connect)
- Hostapd + Dnsmasq (WLAN Hotspot)
- Avahi (anlage.local mDNS)
- Bluetooth Stack

---

## 🚀 Erster Start — WLAN einrichten

Nach dem Neustart öffnet der Pi automatisch einen Hotspot wenn kein WLAN gespeichert ist.

### Schritt 1 — Mit Hotspot verbinden

Auf deinem Handy oder Laptop:

> **WLAN:** `Pi-Radio-Setup`  
> **Passwort:** keins

### Schritt 2 — Setup-Seite öffnen

Browser öffnen → Die Seite öffnet sich automatisch.  
Falls nicht: **`http://192.168.4.1`** eingeben

![Setup Seite](https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radi/main/screenshots/setup.png)

### Schritt 3 — WLAN auswählen

1. Dein Heimnetzwerk aus der Liste wählen
2. WLAN-Passwort eingeben
3. **Verbinden** klicken

### Schritt 4 — IP notieren!

Nach ca. 30 Sekunden erscheint die **IP-Adresse** des Pi groß auf dem Bildschirm — diese notieren oder kopieren.

> **Zuhause im Heimnetz:** `http://anlage.local`  
> **Falls anlage.local nicht funktioniert** (z.B. Firmen- oder Gastnetz): die angezeigte IP direkt verwenden, z.B. `http://172.18.124.125`

---

## 🎛️ Weboberfläche

![Radio Interface](https://raw.githubusercontent.com/GmhF3NiX/Pi-Bluetooth-Wlan-Radi/main/screenshots/radio.png)

### Sender wählen

Klicke einfach auf einen der vorinstallierten Sender — er spielt sofort.

**Vorinstallierte Sender:**
- Pop: SWR3, WDR 2, Bayern 3, NDR 2, 1LIVE
- News: Deutschlandfunk
- Rock: Radio Bob, Rock Antenne
- Jazz: Jazz Radio
- Klassik: Klassik Radio
- Electronic: Energy Berlin, sunshine live

### Eigene Sender hinzufügen

1. Auf **+** klicken
2. Name, Stream-URL und Genre eingeben
3. Speichern → Sender erscheint sofort in der Liste

### Lautstärke

Lautstärke über den Schieberegler anpassen.

---

## 🎵 Spotify Connect

### Zuhause (Heimnetz)

1. **Spotify** auf dem Handy öffnen
2. Unten auf das **Gerät-Symbol** tippen
3. **Pi-Radio** auswählen

Der Pi spielt jetzt deinen Spotify-Stream — das Handy kann gesperrt werden.

### Unterwegs / auf Arbeit (optional: Tailscale)

Zuhause im Heimnetz funktioniert Spotify Connect ohne weitere Einrichtung. In Firmen- oder Gastnetzwerken wird mDNS oft blockiert — mit **Tailscale** geht es trotzdem.

#### Schritt 1 — Tailscale Account erstellen

Kostenlosen Account auf **[tailscale.com](https://tailscale.com)** erstellen (Google oder GitHub Login).

#### Schritt 2 — Tailscale auf dem Pi installieren

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

Den angezeigten Link im Browser öffnen und mit deinem Tailscale-Account einloggen.

#### Schritt 3 — Tailscale-IP herausfinden

```bash
tailscale ip
```

Beispiel: `100.88.156.2`

#### Schritt 4 — Raspotify konfigurieren

```bash
sudo nano /etc/raspotify/conf
```

Diese Zeilen anpassen (mit deiner Tailscale-IP):

```
LIBRESPOT_ZEROCONF_INTERFACE=100.88.156.2
LIBRESPOT_AP_PORT=443
```

```bash
sudo systemctl restart raspotify
```

#### Schritt 5 — Tailscale auf dem Handy

**Tailscale App** installieren → mit gleichem Account einloggen → fertig.

Spotify Connect findet jetzt **Pi-Radio** in jedem Netzwerk.

---

## 🔵 Bluetooth

1. In der Weboberfläche auf **Bluetooth** klicken
2. Pi erscheint als `Pi-Radio` auf deinem Handy
3. Handy koppeln → Musik streamen
4. Zum Beenden wieder auf **Bluetooth** klicken

---

## 📶 WLAN wechseln

Falls du in ein anderes Netzwerk wechseln möchtest:

1. In der Weboberfläche auf **WLAN Reset** klicken
2. Pi startet neu und öffnet den Hotspot `Pi-Radio-Setup`
3. Hotspot verbinden → Setup-Seite → neues WLAN eingeben

---

## 🏠 Home Assistant Integration

Im Ordner `homeassistant/` findest du fertige Konfigurationsdateien.

### Was wird eingebunden:

- **`sensor.pi_radio`** — Status (playing/idle), Sendername, Lautstärke
- **REST Commands** — play, stop, Lautstärke, Bluetooth, Spotify
- **Input Select** — Sender direkt aus HA wechseln
- **Automation** — Sender wechselt automatisch bei Input Select Änderung

### Einrichten:

1. Inhalt von `homeassistant/configuration.yaml` in deine HA `configuration.yaml` einfügen
2. Inhalt von `homeassistant/automations.yaml` in deine HA `automations.yaml` einfügen
3. IP-Adresse des Pi anpassen (Standard: `192.168.178.28`)
4. HA neu starten

### Lovelace Dashboard Karte:

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Pi Radio
    entities:
      - entity: sensor.pi_radio
        name: Status
        icon: mdi:radio
      - entity: input_select.pi_radio_station
        name: Sender
        icon: mdi:music-note
  - type: horizontal-stack
    cards:
      - type: button
        name: Stop
        icon: mdi:stop
        tap_action:
          action: call-service
          service: rest_command.pi_radio_stop
      - type: button
        name: Bluetooth
        icon: mdi:bluetooth
        tap_action:
          action: call-service
          service: rest_command.pi_radio_bt_on
      - type: button
        name: Spotify
        icon: mdi:spotify
        tap_action:
          action: call-service
          service: rest_command.pi_radio_spotify_on
```

---

## 🌐 Erreichbarkeit

| Situation | Adresse |
|-----------|---------|
| Heimnetz | `http://anlage.local` |
| anlage.local geht nicht | IP-Adresse aus dem Setup verwenden |
| Kein WLAN gespeichert | Hotspot `Pi-Radio-Setup` → `http://192.168.4.1` |
| Unterwegs mit Tailscale | Tailscale-IP des Pi |

---

## 🔧 Troubleshooting

**`anlage.local` nicht erreichbar?**
- Windows: mDNS kann etwas dauern, kurz warten
- HA/VM: IP-Adresse direkt verwenden statt `.local`

**Kein Ton?**
- USB DAC verbunden? Evtl. neu einstecken
- `aplay -l` — zeigt verfügbare Audiogeräte

**Hotspot erscheint nicht?**
- Pi neu starten (Strom aus/ein)
- Nach ~15 Sekunden erscheint `Pi-Radio-Setup`

**Spotify verbindet sich nicht?**
- Raspotify läuft? `sudo systemctl status raspotify`
- Tailscale aktiv? `tailscale status`

---

Made with ❤️ by Olli

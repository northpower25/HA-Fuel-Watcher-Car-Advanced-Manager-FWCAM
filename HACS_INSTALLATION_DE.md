# HACS Installationsanleitung

Dieses Repository enthält die **Fuel Watcher Car Advanced Manager** Integration, die eine integrierte Frontend-Karte für Ihr Dashboard enthält.

## Was ist enthalten

Wenn Sie diese Integration über HACS installieren, erhalten Sie:
1. **FWCAM Integration** - Die Backend Home Assistant Integration
2. **FWCAM Karte** - Die Frontend-Karte (wird automatisch registriert)

**Wichtig**: Sie müssen nur die Integration installieren. Die Lovelace-Karte ist automatisch in der Integration enthalten und steht nach der Installation zur Verfügung.

## Voraussetzungen

- Home Assistant 2023.1.0 oder neuer
- HACS (Home Assistant Community Store) installiert

## Installationsschritte

### Schritt 1: Benutzerdefiniertes Repository hinzufügen

1. Öffnen Sie HACS in Ihrem Home Assistant
2. Klicken Sie auf **"Integrationen"**
3. Klicken Sie auf die drei Punkte (⋮) oben rechts
4. Wählen Sie **"Benutzerdefinierte Repositories"**
5. Geben Sie die Repository-URL ein:
   ```
   https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM
   ```
6. Wählen Sie **"Integration"** als Kategorie
7. Klicken Sie auf **"Hinzufügen"**

### Schritt 2: Integration installieren

1. Suchen Sie in HACS Integrationen nach **"Fuel Watcher Car Advanced Manager"**
2. Klicken Sie auf die Integration
3. Klicken Sie auf **"Herunterladen"**
4. Wählen Sie die neueste Version
5. Warten Sie, bis der Download abgeschlossen ist

### Schritt 3: Home Assistant neu starten

Starten Sie Home Assistant neu, um die neue Integration und ihre Frontend-Karte zu laden.

### Schritt 4: Integration konfigurieren

1. Gehen Sie zu **Einstellungen → Geräte & Dienste**
2. Klicken Sie auf **"+ Integration hinzufügen"**
3. Suchen Sie nach **"Fuel Watcher Car Advanced Manager"**
4. Folgen Sie dem Konfigurationsassistenten

Für detaillierte Konfigurationsoptionen siehe [INSTALLATION.md](docs/INSTALLATION.md).

### Schritt 5: Browser-Cache leeren

**Wichtig**: Leeren Sie nach dem Neustart Ihren Browser-Cache, um sicherzustellen, dass die Karte geladen wird:
- Chrome/Edge: `Strg+Umschalt+R` (Windows/Linux) oder `Cmd+Shift+R` (Mac)
- Firefox: `Strg+Umschalt+R` (Windows/Linux) oder `Cmd+Shift+R` (Mac)
- Safari: `Cmd+Option+R`

### Schritt 6: Karte zum Dashboard hinzufügen

Die FWCAM-Karte ist jetzt automatisch in Ihrem Lovelace-Dashboard verfügbar:

1. Bearbeiten Sie Ihr Dashboard
2. Klicken Sie auf **"+ Karte hinzufügen"**
3. Suchen Sie nach **"FWCAM Card"** in der Kartenauswahl
4. Konfigurieren Sie die Karte:

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_refueling_log
```

Ersetzen Sie `mein_auto` durch Ihren Fahrzeugnamen aus der Integrationskonfiguration.

Für detaillierte Kartenkonfiguration siehe [Kartenkonfiguration](#kartenkonfiguration) unten.

## Kartenkonfiguration

Die FWCAM-Karte unterstützt die folgenden Konfigurationsoptionen:

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_refueling_log  # Erforderlich: Ihr Tankvorgänge-Sensor
title: "Mein Auto Tankhistorie"         # Optional: Benutzerdefinierter Titel
show_statistics: true                    # Optional: Statistik-Panel anzeigen
max_entries: 10                          # Optional: Maximale Anzahl anzuzeigender Einträge
```

## Fehlerbehebung

### Karte erscheint nicht in der Kartenauswahl

1. Stellen Sie sicher, dass Sie Home Assistant nach der Installation neu gestartet haben
2. Leeren Sie Ihren Browser-Cache (Hard Refresh)
3. Prüfen Sie die Browser-Konsole auf Fehler (F12 → Konsole)
4. Überprüfen Sie, ob die Integration geladen ist: Einstellungen → System → Protokolle

### "Custom element doesn't exist: fwcam-card"

Dieser Fehler bedeutet, dass das Karten-JavaScript nicht geladen wurde:
1. Leeren Sie den Browser-Cache vollständig
2. Starten Sie Home Assistant neu
3. Versuchen Sie einen anderen Browser, um Cache-Probleme auszuschließen
4. Prüfen Sie, ob die Integration korrekt installiert ist

### Updates

Um die Integration (und Karte) zu aktualisieren:
1. Gehen Sie zu HACS → Integrationen
2. Finden Sie "Fuel Watcher Car Advanced Manager"
3. Klicken Sie auf "Aktualisieren", falls verfügbar
4. Starten Sie Home Assistant neu
5. Leeren Sie den Browser-Cache

## Migration von separater Karteninstallation

Falls Sie die Karte zuvor separat installiert haben (mit der alten Dual-Repository-Methode):

1. Entfernen Sie die alte Karte aus HACS Frontend (falls installiert)
2. Entfernen Sie alle manuellen `frontend.extra_module_url` Einträge aus configuration.yaml
3. Installieren/aktualisieren Sie die Integration wie oben beschrieben
4. Starten Sie Home Assistant neu
5. Die Karte wird nun von der Integration bereitgestellt

## Support

Für Probleme, Feature-Anfragen oder Fragen:
- [GitHub Issues](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)
- [Dokumentation](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM)

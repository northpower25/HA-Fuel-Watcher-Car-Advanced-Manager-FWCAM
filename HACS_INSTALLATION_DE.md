# HACS Installationsanleitung

Dieses Repository enthält **zwei separate Komponenten**, die über HACS installiert werden können:

1. **FWCAM Integration** - Die Backend Home Assistant Integration
2. **FWCAM Lovelace Card** - Die Frontend-Karte für das Dashboard

Beide können aus demselben Repository installiert werden, werden aber von HACS als separate Komponenten erkannt.

## Voraussetzungen

- Home Assistant 2023.1.0 oder neuer
- HACS (Home Assistant Community Store) installiert

## Installation der Integration

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

Starten Sie Home Assistant neu, um die neue Integration zu laden.

### Schritt 4: Integration konfigurieren

1. Gehen Sie zu **Einstellungen → Geräte & Dienste**
2. Klicken Sie auf **"+ Integration hinzufügen"**
3. Suchen Sie nach **"Fuel Watcher Car Advanced Manager"**
4. Folgen Sie dem Konfigurationsassistenten

Für detaillierte Konfigurationsoptionen siehe [INSTALLATION.md](docs/INSTALLATION.md).

## Installation der Lovelace-Karte

### Schritt 1: Benutzerdefiniertes Repository hinzufügen (falls noch nicht geschehen)

1. Öffnen Sie HACS in Ihrem Home Assistant
2. Klicken Sie auf **"Frontend"**
3. Klicken Sie auf die drei Punkte (⋮) oben rechts
4. Wählen Sie **"Benutzerdefinierte Repositories"**
5. Geben Sie die **gleiche Repository-URL** ein:
   ```
   https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM
   ```
6. Wählen Sie **"Lovelace"** als Kategorie
7. Klicken Sie auf **"Hinzufügen"**

### Schritt 2: Karte installieren

1. Suchen Sie in HACS Frontend nach **"FWCAM Lovelace Card"**
2. Klicken Sie auf die Karte
3. Klicken Sie auf **"Herunterladen"**
4. Wählen Sie die neueste Version
5. Warten Sie, bis der Download abgeschlossen ist

### Schritt 3: Home Assistant neu starten

Starten Sie Home Assistant neu, um die Kartenressourcen zu laden.

### Schritt 4: Browser-Cache leeren

**Wichtig**: Leeren Sie nach dem Neustart Ihren Browser-Cache:
- Chrome/Edge: `Strg+Umschalt+R` (Windows/Linux) oder `Cmd+Shift+R` (Mac)
- Firefox: `Strg+Umschalt+R` (Windows/Linux) oder `Cmd+Shift+R` (Mac)
- Safari: `Cmd+Option+R`

### Schritt 5: Karte zum Dashboard hinzufügen

1. Bearbeiten Sie Ihr Dashboard
2. Klicken Sie auf **"+ Karte hinzufügen"**
3. Suchen Sie nach **"FWCAM Card"** in der Kartenauswahl
4. Konfigurieren Sie die Karte:

```yaml
type: custom:fwcam-card
entity: sensor.mein_auto_refueling_log
```

Ersetzen Sie `mein_auto` durch Ihren Fahrzeugnamen aus der Integrationskonfiguration.

Für detaillierte Kartenkonfiguration siehe [fwcam-card/README_DE.md](fwcam-card/README_DE.md).

## Fehlerbehebung

### Integration wird nicht in HACS angezeigt

- Stellen Sie sicher, dass Sie **"Integration"** als Kategorie gewählt haben
- Aktualisieren Sie HACS
- Überprüfen Sie, ob das Repository erfolgreich hinzugefügt wurde

### Karte wird nicht in HACS angezeigt

- Stellen Sie sicher, dass Sie **"Lovelace"** als Kategorie beim Hinzufügen des Repositories gewählt haben
- Aktualisieren Sie den HACS Frontend-Bereich
- Überprüfen Sie, ob das Repository erfolgreich hinzugefügt wurde

### Karte lädt nicht im Dashboard

- Überprüfen Sie, ob Sie Home Assistant nach der Installation neu gestartet haben
- Leeren Sie Ihren Browser-Cache (sehr wichtig!)
- Überprüfen Sie die Browser-Konsole auf Fehler (F12)
- Überprüfen Sie, ob die Ressource geladen ist: **Einstellungen → Dashboards → Ressourcen**

### Karte zeigt "Custom element doesn't exist"

Dies bedeutet normalerweise:
1. Browser-Cache wurde nicht geleert - leeren Sie ihn und aktualisieren Sie
2. Ressource wurde nicht geladen - überprüfen Sie den Ressourcen-Bereich
3. Falscher Kartentyp - stellen Sie sicher, dass Sie `type: custom:fwcam-card` verwenden

## Versionskompatibilität

Beide Komponenten (Integration und Karte) sollten für beste Kompatibilität auf derselben Version gehalten werden.

Beim Aktualisieren:
1. Aktualisieren Sie die Integration über HACS Integrationen
2. Aktualisieren Sie die Karte über HACS Frontend
3. Starten Sie Home Assistant neu
4. Leeren Sie den Browser-Cache

## Support

Für Probleme und Fragen:
- Prüfen Sie die [Dokumentation](docs/)
- Lesen Sie die [Fehlerbehebungsanleitung](docs/TROUBLESHOOTING.md)
- Öffnen Sie ein [Issue](https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/issues)

## Vorteile der HACS-Installation

- ✅ Einfache Installation und Updates
- ✅ Automatische Versionsverwaltung
- ✅ Integriert mit Home Assistant
- ✅ Community-Support
- ✅ Ein-Klick-Updates

## Alternative: Manuelle Installation

Wenn Sie eine manuelle Installation bevorzugen oder HACS nicht verfügbar ist, siehe:
- Integration: [INSTALLATION.md](docs/INSTALLATION.md#method-2-manual-installation)
- Karte: [fwcam-card/README_DE.md](fwcam-card/README_DE.md#manuelle-installation)

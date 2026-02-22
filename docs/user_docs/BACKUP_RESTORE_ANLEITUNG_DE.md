# Backup & Wiederherstellung – Anleitung

Diese Anleitung erklärt, wie du deine haFWCMA-Fahrzeugdaten sichern und
wiederherstellen kannst.

---

## Überblick

haFWCMA speichert alle Fahrzeugdaten (Tankvorgänge, Fahrtenbuch, Kilometerstand-
Verlauf, ML-Modelle usw.) im internen Speicher von Home Assistant. Die Integration
bietet zwei Services zum Schutz dieser Daten:

| Service | Zweck |
|---------|-------|
| `hafwcma.create_backup` | Exportiert einen Schnappschuss aller Daten in eine JSON-Datei |
| `hafwcma.restore_backup` | Importiert einen zuvor erstellten Schnappschuss zurück in die Integration |

Außerdem gibt es eine **Button-Entität** (`button.<fahrzeug>_create_backup`), die
`create_backup` per Klick aus dem Dashboard oder der Entitätenansicht auslöst.

---

## Was enthält ein Backup?

Ein Backup enthält alle **nutzererzeugten Daten** für einen Fahrzeugeintrag:

- Tankvorgänge und Kilometerstand-Verlauf
- Fahrtenbuch (Fahrten, Muster, POIs)
- Preishistorie und zuletzt bekannte Kraftstoffdaten
- ML/Vorhersagemodelle
- Geocoding-Cache (für schnellere Adressanzeige nach der Wiederherstellung)

Laufzeit-Caches und Sensorzustände, die neu berechnet werden können, sind **nicht**
enthalten.

---

## Backup erstellen

### Variante A – Button-Entität (einfachste Methode)

1. Öffne Home Assistant → **Entitäten**.
2. Suche nach `button.<fahrzeugname>_create_backup` und klicke auf **Aktivieren**.
3. Eine HA-Benachrichtigung erscheint mit der Download-URL, z. B.:
   ```
   /local/hafwcma_backups/hafwcma_backup_MeinAuto_20260101_120000.json
   ```
4. Öffne diese URL im Browser (`http://homeassistant.local:8123/local/hafwcma_backups/…`),
   um die Datei herunterzuladen.

### Variante B – Service-Aufruf

1. Öffne **Entwickler-Werkzeuge → Dienste**.
2. Wähle den Service: `hafwcma.create_backup`.
3. Trage deine `config_entry_id` ein (siehe [Config-Entry-ID herausfinden](#config-entry-id-herausfinden)).
4. Klicke auf **Dienst aufrufen**.
5. Die HA-Benachrichtigung zeigt den Dateipfad und die Download-URL.

Die Backup-Datei wird gespeichert unter:
```
/config/www/hafwcma_backups/hafwcma_backup_<fahrzeug>_<zeitstempel>.json
```

> 💡 **Tipp:** Speichere Backup-Dateien außerhalb von Home Assistant (z. B. auf
> deinem PC oder in einem Cloud-Speicher). Der Ordner `/config/www/hafwcma_backups/`
> ist zwar über den HA-Webserver erreichbar, wird aber **nicht** in HA's eigenem
> Backup-System berücksichtigt.

---

## Backup wiederherstellen

### Voraussetzungen

- Die Backup-Datei muss sich auf dem **Home Assistant-Server** befinden (nicht nur
  auf deinem lokalen PC).
- Falls du nach einer Neuinstallation wiederherstellst, schließe zuerst die
  Integrations-Einrichtung ab, damit der Zieleintrag (`config_entry_id`) existiert.

### Schritt für Schritt

1. **Backup-Datei auf den HA-Server hochladen.**

   Kopiere die Datei nach `/config/www/hafwcma_backups/` – mögliche Methoden:
   - **File Editor Add-on** – Upload über den integrierten Browser
   - **Samba / Netzwerkfreigabe** – `/config` einbinden und Datei kopieren
   - **SSH / Terminal Add-on** – `scp` oder manuelles Kopieren

2. **Den absoluten Dateipfad notieren**, z. B.:
   ```
   /config/www/hafwcma_backups/hafwcma_backup_MeinAuto_20260101_120000.json
   ```

3. **Restore-Service aufrufen.**

   Öffne **Entwickler-Werkzeuge → Dienste**, wähle `hafwcma.restore_backup`
   und gib folgende Felder an:

   | Feld | Wert |
   |------|------|
   | `config_entry_id` | Die Eintrags-ID des Fahrzeugs, in das du wiederherstellen möchtest (siehe unten) |
   | `backup_file_path` | Absoluter Pfad zur Backup-Datei auf dem HA-Server |
   | `force` | `false` (Standard) – nur auf `true` setzen, um weiche Warnungen zu übergehen |

4. **Auf die Benachrichtigung warten.**

   Bei Erfolg erscheint:
   > ✅ Backup wiederhergestellt für **Mein Auto**.
   > Bitte lade die Integration neu (oder starte Home Assistant neu), um die
   > wiederhergestellten Daten zu übernehmen.

5. **Integration neu laden.**

   Öffne **Einstellungen → Geräte & Dienste**, suche haFWCMA und klicke auf
   **Neu laden**. Alternativ kann Home Assistant neugestartet werden.

---

## Häufig gestellte Fragen

### Findet die Wiederherstellung während der Einrichtung (Config Flow) statt?

Nein. Die Wiederherstellung erfolgt **nach** der Einrichtung, über den Service
`hafwcma.restore_backup`. Du richtest die Integration zuerst normal ein (Config Flow),
damit ein Eintrag existiert, und rufst dann den Restore-Service auf, um ihn mit
deinen gesicherten Daten zu befüllen.

### Woher weiß die Integration, zu welchem Fahrzeug die Daten gehören?

Der Parameter `config_entry_id` identifiziert den Zieleintrag. Du gibst ihn beim
Service-Aufruf an. Die Backup-Datei enthält den Fahrzeugnamen und die ursprüngliche
Eintrags-ID als Metadaten – diese sind jedoch nur informativ. Die Wiederherstellung
schreibt immer in den von dir angegebenen Eintrag.

### Kann ich in eine bestehende Installation mit vorhandenen Daten wiederherstellen?

Ja. Der Restore **überschreibt** alle Schlüssel, die im Backup vorhanden sind.
Vorhandene Daten für diese Schlüssel werden ersetzt. Es findet **keine
Duplikat-Erkennung** statt – da das Backup die aktuellen Daten vollständig ersetzt,
existiert jeder Tankvorgang oder jede Fahrt danach nur einmal.

### Was passiert nach einer Neuinstallation der Integration?

Nach der Neuinstallation von haFWCMA:
1. Schließe den Config Flow ab, um einen neuen Eintrag für dein Fahrzeug zu erstellen.
2. Kopiere deine Backup-Datei nach `/config/www/hafwcma_backups/` auf dem HA-Server.
3. Rufe `hafwcma.restore_backup` mit der **neuen** `config_entry_id` auf.

Die Integration stellt alle historischen Daten in den neuen Eintrag wieder her.

### Was ist mit der Kompatibilität zwischen Versionen?

Die Backup-Datei enthält die haFWCMA-Version, mit der sie erstellt wurde. Beim
Wiederherstellen prüft die Integration automatisch die Kompatibilität:

- **Kompatibel (ggf. mit Warnungen)** – Wiederherstellung läuft durch. Eine Warnung
  wird angezeigt, wenn das Backup von einer älteren Version stammt, aber keine
  kritischen Änderungen erkannt wurden.
- **Inkompatibel (harter Fehler)** – Wiederherstellung wird blockiert. Dies tritt
  auf, wenn zwischen der Backup-Version und der aktuellen Version eine kritische
  Änderung eingeführt wurde. Die Fehlermeldung erklärt, was sich geändert hat und
  was zu tun ist.

`force: true` umgeht nur **weiche Warnungen** – harte Fehler werden damit nicht
übergangen.

---

## Config-Entry-ID herausfinden

Die `config_entry_id` ist die eindeutige Kennung deines haFWCMA-Eintrags für ein
bestimmtes Fahrzeug. So findest du sie:

1. Öffne **Einstellungen → Geräte & Dienste → Integrationen**.
2. Klicke auf deine haFWCMA-Integration.
3. In der URL-Leiste erscheint etwas wie:
   ```
   /config/integrations/integration/hafwcma?config_entry=abc123def456
   ```
   Der Wert nach `config_entry=` ist deine `config_entry_id`.

Alternativ enthält das Service-Ergebnis von `hafwcma.create_backup` das Feld
`entry_id`.

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| „Backup-Datei nicht gefunden" | Überprüfe, ob der Dateipfad korrekt ist und die Datei sich auf dem **HA-Server** befindet (nicht nur auf deinem PC). |
| „Inkompatibles Backup"-Fehler | Aktualisiere haFWCMA auf die neueste Version oder folge dem Migrationshinweis in der Fehlermeldung. |
| Daten nicht aktualisiert nach Restore | Lade die Integration neu (**Einstellungen → Geräte & Dienste → Neu laden**) oder starte HA neu. |
| Button-Entität nicht sichtbar | Stelle sicher, dass der Fahrzeugeintrag geladen ist. Öffne **Einstellungen → Geräte & Dienste** und prüfe, ob haFWCMA ohne Fehler läuft. |

---

## Verwandte Dokumente

- [Fehlerbehebung (EN)](TROUBLESHOOTING.md)
- [Datenspeicherung (EN)](DATA_STORAGE.md)

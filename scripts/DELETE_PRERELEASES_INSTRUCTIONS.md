# Anleitung zum Löschen aller Pre-Releases vor v0.1.0

## Übersicht
Dieses Dokument beschreibt, wie alle 29 Pre-Releases (v0.0.82 bis v0.0.110) vor dem aktuellen Release v0.1.0 gelöscht werden können.

## Gefundene Pre-Releases
Folgende Pre-Releases wurden identifiziert und können gelöscht werden:
- v0.0.110 bis v0.0.82 (insgesamt 29 Pre-Releases)

## Methode 1: Automatisches Skript (Empfohlen)

### Voraussetzungen
- GitHub CLI (`gh`) installiert: https://cli.github.com/
- Authentifiziert mit GitHub: `gh auth login`

### Schritte
1. Skript ausführbar machen:
   ```bash
   chmod +x scripts/delete_prereleases.sh
   ```

2. Testlauf durchführen (zeigt nur an, was gelöscht würde):
   ```bash
   ./scripts/delete_prereleases.sh --dry-run
   ```

3. Pre-Releases tatsächlich löschen:
   ```bash
   ./scripts/delete_prereleases.sh
   ```

## Methode 2: GitHub CLI (manuell)

Sie können Pre-Releases einzeln mit dem GitHub CLI löschen:

```bash
gh release delete v0.0.110 --repo northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM --yes
gh release delete v0.0.109 --repo northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM --yes
# ... und so weiter für alle Pre-Releases
```

## Methode 3: GitHub Web Interface

1. Gehen Sie zu: https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/releases
2. Für jedes Pre-Release:
   - Klicken Sie auf das Pre-Release
   - Klicken Sie auf "Delete" (Löschen)
   - Bestätigen Sie die Löschung

## Hinweis
Nach dem Löschen der Pre-Releases bleiben nur die stabilen Releases (wie v0.1.0) in Ihrem Repository erhalten.

---

# Instructions for Deleting All Pre-Releases Before v0.1.0

## Overview
This document describes how to delete all 29 pre-releases (v0.0.82 to v0.0.110) before the current release v0.1.0.

## Identified Pre-Releases
The following pre-releases have been identified and can be deleted:
- v0.0.110 to v0.0.82 (total of 29 pre-releases)

## Method 1: Automated Script (Recommended)

### Prerequisites
- GitHub CLI (`gh`) installed: https://cli.github.com/
- Authenticated with GitHub: `gh auth login`

### Steps
1. Make the script executable:
   ```bash
   chmod +x scripts/delete_prereleases.sh
   ```

2. Perform a dry-run (shows what would be deleted):
   ```bash
   ./scripts/delete_prereleases.sh --dry-run
   ```

3. Actually delete the pre-releases:
   ```bash
   ./scripts/delete_prereleases.sh
   ```

## Method 2: GitHub CLI (manual)

You can delete pre-releases individually using the GitHub CLI:

```bash
gh release delete v0.0.110 --repo northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM --yes
gh release delete v0.0.109 --repo northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM --yes
# ... and so on for all pre-releases
```

## Method 3: GitHub Web Interface

1. Go to: https://github.com/northpower25/HA-Fuel-Watcher-Car-Advanced-Manager-FWCAM/releases
2. For each pre-release:
   - Click on the pre-release
   - Click "Delete"
   - Confirm the deletion

## Note
After deleting the pre-releases, only stable releases (like v0.1.0) will remain in your repository.

# Feature: API-Testing im Config Flow

**Status**: Deferred / In Planung  
**Priorität**: Mittel  
**Geschätzter Aufwand**: 15-20 Stunden  
**Version**: Geplant für v1.0.0 oder später  

## Übersicht

Dieses Feature fügt API-Validierung und Testfunktionalität während des Konfigurations-Flows hinzu, um Benutzern sofortiges Feedback über die Korrektheit ihrer API-Konfiguration zu geben.

## Problem Statement

Aktuell gibt es im Setup-/Config Flow folgende Probleme:

1. **Tankpreis-API**: Es erfolgt keine Validierung der API-Konfiguration während des Setups. Benutzer erfahren erst nach Abschluss der Konfiguration, ob ihre API-Zugangsdaten korrekt sind.

2. **Telegram-API**: Es gibt keine Möglichkeit zu testen, ob die Telegram-Konfiguration funktioniert und ob Nachrichten erfolgreich gesendet/empfangen werden können.

## User Stories

### Story 1: Tankpreis-API Validierung
**Als** Benutzer  
**Möchte ich** während der Konfiguration testen, ob meine Tankpreis-API-Zugangsdaten korrekt sind  
**Damit** ich sicher sein kann, dass die Integration funktioniert, bevor ich die Konfiguration abschließe

**Akzeptanzkriterien:**
- Nach Eingabe der API-Konfiguration (Provider, API-Key, Radius, Fuel Type)
- Wird beim Klick auf "OK" eine Testabfrage an die API durchgeführt
- Ein neues Fenster zeigt das Ergebnis:
  - **Bei Erfolg**: Liste der gefundenen günstigsten Tankstellen in der Nähe des Zuhauses
    - Name der Tankstelle
    - Adresse
    - Preise für e5, e10, Diesel
    - "OK"-Button zum Fortfahren
  - **Bei Fehler**: Vollständige Fehlermeldung der API
    - Technischer Fehlercode
    - Lesbare Fehlerbeschreibung
    - "Zurück"-Button zur API-Konfiguration

### Story 2: Telegram-API Validierung
**Als** Benutzer  
**Möchte ich** während der Konfiguration testen, ob meine Telegram-Integration funktioniert  
**Damit** ich sicher sein kann, dass ich Benachrichtigungen empfangen und darauf antworten kann

**Akzeptanzkriterien:**
- Nach Eingabe der Telegram-Konfiguration (Bot Token, Chat ID)
- Wird beim Klick auf "OK" eine Testnachricht gesendet
- Testnachricht-Inhalt:
  - **Titel**: "FWCAM Testnachricht"
  - **Text**: "Dein Auto sagt: 'Ich bin bereit für die Benachrichtigung zu intelligenten Tankentscheidungen! Bitte antworte auf diese Nachricht damit ich auch prüfen kann ob du mich erreichen kannst'"
  - Mit Rückantwort-Anforderung
- Ein Wartefenster wird angezeigt:
  - Zeigt an, dass eine Testnachricht gesendet wurde
  - Fordert Benutzer auf, auf die Nachricht zu antworten
  - Buttons:
    - "Zurück" - zurück zur Telegram-Konfiguration
    - "Abbrechen" - Setup abbrechen und Integration zurückrollen
- Nach Erhalt der Rückantwort:
  - Anzeige: "Danke für deine folgende Rückmeldung: [Text der Antwort] jetzt kann ich auch Informationen von dir erhalten :-)"
  - "OK"-Button erscheint zum Fortfahren

## Technische Anforderungen

### Architektur-Änderungen

1. **Async Validation Flow**
   - Neue Config Flow Steps für Validierung
   - Asynchrone API-Aufrufe während der Konfiguration
   - State-Management für mehrstufige Validierung

2. **Tankpreis-API Testing**
   - Implementierung einer `async_validate_fuel_api()` Funktion
   - Nutzung der Home-Koordinaten als Teststandort
   - Fehlerbehandlung für verschiedene API-Fehlerfälle
   - Formatierung der Stationsergebnisse für UI-Anzeige

3. **Telegram-API Testing**
   - Implementierung einer `async_validate_telegram_api()` Funktion
   - Senden einer Testnachricht
   - Webhook oder Polling-basiertes Warten auf Antwort
   - Timeout-Handling (z.B. 2 Minuten)
   - State-Management für Antwort-Wartezeit

### Config Flow Struktur

```
async_step_user (API-Konfiguration)
  ↓
async_step_validate_api (NEU - API Test)
  ↓ [Erfolg]
async_step_vehicle
  ↓
async_step_vehicle_entities
  ↓
async_step_telegram
  ↓
async_step_validate_telegram (NEU - Telegram Test)
  ↓ [Wartet auf Antwort]
async_step_telegram_response (NEU - Antwort verarbeitet)
  ↓ [Erfolg]
async_step_prediction
```

### Neue Config Flow Steps

#### Step: `async_step_validate_api`
```python
async def async_step_validate_api(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Validate fuel price API configuration."""
    
    if user_input is None:
        # Perform API test
        try:
            # Test API with home coordinates
            stations = await test_api_connection(
                provider=self.data[CONF_PROVIDER],
                api_key=self.data[CONF_API_KEY],
                lat=self.hass.config.latitude,
                lon=self.hass.config.longitude,
                radius=self.data[CONF_RADIUS],
                fuel_type=self.data[CONF_FUEL_TYPE],
            )
            
            # Show success with station list
            return self.async_show_form(
                step_id="validate_api",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "result": "success",
                    "stations": format_stations(stations),
                },
            )
        except Exception as err:
            # Show error message
            return self.async_show_form(
                step_id="validate_api",
                data_schema=vol.Schema({}),
                errors={"base": "api_connection_failed"},
                description_placeholders={
                    "result": "error",
                    "error_message": str(err),
                },
            )
    else:
        # User clicked OK/Back button
        if "back" in user_input:
            return await self.async_step_user()
        return await self.async_step_vehicle()
```

#### Step: `async_step_validate_telegram`
```python
async def async_step_validate_telegram(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Validate Telegram API configuration."""
    
    if user_input is None:
        # Send test message
        try:
            await send_telegram_test_message(
                token=self.data[CONF_TELEGRAM_TOKEN],
                chat_id=self.data[CONF_TELEGRAM_CHAT_ID],
            )
            
            # Store timestamp for timeout
            self._telegram_test_start = datetime.now()
            
            # Show waiting screen
            return self.async_show_form(
                step_id="validate_telegram",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "message": "Test message sent. Please reply to continue.",
                },
            )
        except Exception as err:
            return self.async_show_form(
                step_id="validate_telegram",
                data_schema=vol.Schema({}),
                errors={"base": "telegram_send_failed"},
                description_placeholders={
                    "error_message": str(err),
                },
            )
    else:
        # User action (back/cancel)
        if "cancel" in user_input:
            # Rollback integration
            raise AbortFlow("user_cancelled")
        return await self.async_step_telegram()
```

#### Step: `async_step_telegram_response`
```python
async def async_step_telegram_response(
    self, user_input: dict[str, Any] | None = None
) -> FlowResult:
    """Process Telegram response."""
    
    # This step is triggered by webhook/polling
    response_text = self._telegram_response
    
    return self.async_show_form(
        step_id="telegram_response",
        data_schema=vol.Schema({}),
        description_placeholders={
            "response_text": response_text,
            "message": f"Danke für deine folgende Rückmeldung: {response_text}",
        },
    )
```

### UI/UX Überlegungen

1. **Lade-Indikatoren**: Während API-Aufrufe laufen, Lade-Animation anzeigen
2. **Timeout-Handling**: Klare Timeout-Meldungen (z.B. "Telegram-Antwort nicht innerhalb von 2 Minuten erhalten")
3. **Fehler-Details**: Technische Details in ausklappbaren Bereichen für fortgeschrittene Benutzer
4. **Retry-Mechanismus**: Option zum erneuten Versuch bei Fehlern
5. **Skip-Option**: Fortgeschrittene Benutzer können Tests überspringen

### Abhängigkeiten

- Home Assistant Config Flow Framework
- Telegram Bot API (python-telegram-bot Bibliothek)
- Bestehende Provider-Implementierungen (TankerKönig)
- Async HTTP-Client (aiohttp)

## Implementierungs-Phasen

### Phase 1: API-Validierung (MVP)
**Aufwand**: 8-10 Stunden

- Implementierung `async_step_validate_api`
- API-Test-Funktion für TankerKönig
- Erfolgs- und Fehler-Anzeige
- Zurück-Navigation bei Fehlern

### Phase 2: Telegram-Validierung (Basis)
**Aufwand**: 10-12 Stunden

- Implementierung `async_step_validate_telegram`
- Testnachricht senden
- Einfaches Polling für Antwort (ohne Webhook)
- Timeout-Handling
- Abbruch-Funktionalität

### Phase 3: Verbesserungen (Optional)
**Aufwand**: 5-8 Stunden

- Webhook-basiertes Antwort-Handling (schneller)
- Retry-Mechanismen
- Skip-Optionen
- Erweiterte Fehlerbehandlung
- Logging und Diagnostics

## Risiken und Herausforderungen

1. **Komplexität**: Mehrstufige asynchrone Flows erhöhen die Code-Komplexität erheblich
2. **State-Management**: Zustand zwischen Steps muss korrekt verwaltet werden
3. **Telegram-Timing**: Warten auf Benutzer-Antwort kann zu langen Setup-Zeiten führen
4. **Timeout-Handling**: Korrekte Behandlung von Timeouts ohne Memory-Leaks
5. **Benutzer-Erfahrung**: Zusätzliche Steps könnten als zu komplex empfunden werden
6. **Testing**: Schwierig zu testen ohne echte API-Credentials

## Alternativen

1. **Post-Setup Validierung**: Tests nach Abschluss der Konfiguration über Services
2. **Optional Testing**: Tests als optionaler Button in der Config, nicht im Flow
3. **Separate Test-Integration**: Eigene "Test" Config Entry für Validierung
4. **Dokumentation**: Bessere Fehler-Dokumentation statt automatischer Tests

## Entscheidung

**Deferred** - Feature wird zunächst zurückgestellt aus folgenden Gründen:

1. Hohe Komplexität für marginalen Nutzen
2. Benutzer können API-Konfiguration nach Setup manuell testen
3. Telegram-Test erfordert komplexes State-Management
4. Andere Features haben höhere Priorität
5. Kann später als separate Enhancement hinzugefügt werden

## Nächste Schritte (bei Implementierung)

1. Proof of Concept für API-Validierung
2. Design Review mit Community
3. Implementierung Phase 1
4. Beta-Testing mit ausgewählten Benutzern
5. Feedback-Integration
6. Implementierung Phase 2
7. Vollständiger Release

## Referenzen

- Original Issue: GitHub Discussion vom 2026-02-11
- Config Flow Dokumentation: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- Telegram Bot API: https://core.telegram.org/bots/api
- TankerKönig API: https://creativecommons.tankerkoenig.de

---

**Erstellt**: 2026-02-11  
**Letzte Aktualisierung**: 2026-02-11  
**Autor**: Development Team  
**Status**: Deferred

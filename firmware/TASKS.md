# ESP32 Locomotive Controller - Task List

## Project Status
- **Current Version**: 1.0 (Funktionsfähiger Prototyp)
- **Last Updated**: 2025-08-03
- **Total Tasks**: 29
- **Completed**: 0
- **In Progress**: 0
- **Pending**: 29

---

## KRITISCHE VERBESSERUNGEN (Dringlichkeit: HOCH)

### 1. Speicher-Management und Performance
- [ ] **1.1** Aufteilen von `rocrail_controller.py` (23KB) in kleinere Module
  - [ ] RocrailProtocol Klasse erstellen (`lib/protocol/rocrail_protocol.py`)
  - [ ] ControllerStateMachine Klasse erstellen (`lib/core/controller_state.py`)
  - [ ] Main Controller Klasse implementieren
  - **Status**: Pending
  - **Estimated Effort**: 4 Stunden
  - **Priority**: Critical

- [ ] **1.2** Globale Variablen durch Klassen-basierte Architektur ersetzen
  - [ ] MainController Klasse mit Zustandsverwaltung
  - [ ] Dependency Injection für Hardware-Komponenten
  - **Status**: Pending
  - **Dependencies**: Task 1.1
  - **Estimated Effort**: 3 Stunden

### 2. Socket-Verbindung Stabilität
- [ ] **2.1** Timeout-basierte Verbindungsüberwachung implementieren
  - [ ] Socket-Timeout konfigurierbar machen
  - [ ] Heartbeat-Mechanismus für RocRail-Verbindung
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden
  - **Priority**: Critical

- [ ] **2.2** Robuste Reconnect-Logik implementieren
  - [ ] Exponential Backoff für Wiederverbindungsversuche
  - [ ] Verbindungsstatus-Recovery bei Netzwerkfehlern
  - [ ] Thread-sichere Socket-Operation
  - **Status**: Pending
  - **Estimated Effort**: 3 Stunden

### 3. Konfigurationssicherheit
- [ ] **3.1** WiFi-Credentials sicher speichern
  - [ ] Separate `config.txt` mit .gitignore
  - [ ] Einfache Verschlüsselung oder Encoding
  - **Status**: Pending
  - **Estimated Effort**: 1 Stunde
  - **Priority**: High

---

## WICHTIGE VERBESSERUNGEN (Dringlichkeit: MITTEL)

### 4. Hardware-Abstraktion
- [ ] **4.1** Einheitliche Hardware-Konfiguration
  - [ ] Pin-Definitionen aus `btn_config.py` und `rocrail_config.py` zusammenführen
  - [ ] Hardware-Profile für verschiedene Board-Versionen
  - **Status**: Pending
  - **Estimated Effort**: 1 Stunde

- [ ] **4.2** Hardware-Validierung beim Start
  - [ ] Pin-Verfügbarkeit prüfen
  - [ ] NeoPixel-Funktionalität testen
  - [ ] ADC-Kalibrierung beim Start
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

### 5. XML-Protokoll-Handling
- [ ] **5.1** XML-Builder Klasse für RocRail-Protokoll
  - [ ] Template-basierte XML-Generierung
  - [ ] Validierung der XML-Nachrichten
  - [ ] Header-Größe automatisch berechnen
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

- [ ] **5.2** Verbessertes Buffer-Management
  - [ ] Streaming XML-Parser implementieren
  - [ ] Memory-efficient XML-Processing
  - [ ] Buffer-Overflow-Schutz
  - **Status**: Pending
  - **Estimated Effort**: 3 Stunden

### 6. Status-Management
- [ ] **6.1** Zentrale Status-Manager Klasse
  - [ ] Einheitliche Status-Enums definieren
  - [ ] Status-Änderungs-Events implementieren
  - [ ] LED-Status automatisch synchronisieren
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

### 7. Error Handling & Recovery
- [ ] **7.1** Umfassendes Exception-Handling
  - [ ] Try-catch Blöcke für alle kritischen Operationen
  - [ ] Graceful Degradation bei Hardware-Fehlern
  - [ ] Error-Recovery-Strategien
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

---

## OPTIMIERUNGEN (Dringlichkeit: NIEDRIG)

### 8. Code-Qualität
- [ ] **8.1** Lange Funktionen aufteilen
  - [ ] `handle_data()` Funktion refactoren
  - [ ] Main loop in State Pattern umwandeln
  - [ ] Funktionen unter 50 Zeilen halten
  - **Status**: Pending
  - **Estimated Effort**: 3 Stunden

- [ ] **8.2** Code-Dokumentation verbessern
  - [ ] Docstrings für alle öffentlichen Methoden
  - [ ] Inline-Kommentare für komplexe Logik
  - [ ] README_DEVELOPMENT.md aktualisieren
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

### 9. Logging und Debugging
- [ ] **9.1** Logger-Klasse implementieren
  - [ ] Log-Levels (DEBUG, INFO, WARNING, ERROR)
  - [ ] Konfigurierbare Log-Ausgabe
  - [ ] Memory-efficient Logging für MicroPython
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

- [ ] **9.2** Debug-Interface über Web
  - [ ] Live-Status über Web-Interface
  - [ ] Log-Viewer im Configuration Mode
  - **Status**: Pending
  - **Estimated Effort**: 3 Stunden

### 10. Erweiterte Funktionalität
- [ ] **10.1** Sound-Button Implementierung
  - [ ] RocRail-Sound-Funktionen (Horn, Bell)
  - [ ] Multiple Sound-Events unterstützen
  - **Status**: Pending
  - **Estimated Effort**: 1 Stunde

- [ ] **10.2** Erweiterte Lokomotiv-Unterstützung
  - [ ] Paging für mehr als 5 Lokomotiven
  - [ ] Lokomotiv-Gruppen/Favoriten
  - [ ] Lokomotiv-Details anzeigen
  - **Status**: Pending
  - **Estimated Effort**: 4 Stunden

---

## STRUKTURELLE VERBESSERUNGEN

### 11. Datei-Organisation
- [ ] **11.1** Module-Struktur implementieren
```
lib/
├── hardware/          # Hardware-abstraction
│   ├── neopixel_controller.py
│   ├── button_controller.py  
│   └── poti_controller.py
├── protocol/          # Communication protocols
│   ├── rocrail_protocol.py
│   └── xml_builder.py
├── controllers/       # Business logic controllers
│   ├── locomotive_controller.py
│   └── wifi_controller.py
└── core/             # Core system components
    ├── status_manager.py
    ├── logger.py
    └── config_manager.py
```
- **Status**: Pending
- **Estimated Effort**: 3 Stunden

### 12. Konfiguration optimieren
- [ ] **12.1** Konfigurationssystem überarbeiten
  - [ ] Sensitive Daten in separate Dateien
  - [ ] Hardware-Profile für verschiedene Boards
  - [ ] Runtime-Konfiguration über Web-Interface
  - **Status**: Pending
  - **Estimated Effort**: 2 Stunden

### 13. Testing & Validation
- [ ] **13.1** Unit-Tests implementieren
  - [ ] Hardware-Controller Tests
  - [ ] Protocol-Handler Tests
  - [ ] Mocking für Hardware-Komponenten
  - **Status**: Pending
  - **Estimated Effort**: 4 Stunden

---

## COMPLETED TASKS

### ✅ Grundfunktionalität
- [x] 10 NeoPixel LED-System implementiert
- [x] RocRail-Verbindung und Socket-Kommunikation
- [x] Lokomotiv-Auswahl und Geschwindigkeitssteuerung
- [x] WiFi-Konfiguration über Web-Interface
- [x] Button-Controller mit Entprellung

---

## NOTES & DECISIONS

### Design Decisions
- **MicroPython Compatibility**: Alle Lösungen müssen MicroPython-kompatibel sein
- **Memory Constraints**: ESP32 hat begrenzte RAM-Ressourcen
- **Battery Operation**: Code muss energie-effizient sein
- **Real-time Requirements**: Steuerungsbefehle müssen schnell übertragen werden

### Technical Debt
- Große `rocrail_controller.py` Datei macht Wartung schwierig
- Globale Variablen erschweren Testing und Debugging
- Manueller XML-String-Bau ist fehleranfällig
- Fehlende Abstraktion zwischen Hardware und Business Logic

### Future Considerations
- OTA-Updates für Firmware
- Erweiterte Lokomotiv-Funktionen (F1-F12)
- Multiple Controller-Support
- Integration mit anderen Modellbahn-Systemen

---

## COMMIT MESSAGE TEMPLATES

```
feat: Add new functionality
fix: Correct existing issue  
refactor: Code restructure without behavior change
docs: Documentation updates
perf: Performance improvements
test: Add or update tests
chore: Maintenance tasks
```

---

**Legend**: 
- ⏳ In Progress
- ✅ Completed  
- ❌ Blocked
- 🔄 Review Required
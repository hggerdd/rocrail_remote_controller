# ESP32 Locomotive Controller - Task List

## Project Status
- **Current Version**: 1.2 (Unified Hardware Configuration)
- **Last Updated**: 2025-08-04
- **Total Tasks**: 29
- **Completed**: 2
- **In Progress**: 0
- **Pending**: 27

## 🎯 Recent Achievements
- **✅ Task 4.1 Completed (2025-08-04)**: Unified Hardware Configuration
  - Merged `btn_config.py` and `rocrail_config.py` into unified system
  - Created `hardware_config.py` for hardware pin definitions and LED mappings  
  - Created `config.py` for application settings (WiFi, RocRail, timing)
  - Fixed WiFi-Config-Server NeoPixel conflict (6→10 LEDs)
  - Fixed boot.py bug (green_button check corrected)
  - Successfully migrated all imports across the project

- **✅ Task 1.1 Completed (2025-08-04)**: Major architectural refactoring
  - Reduced main controller from 26KB to 11KB (~60% size reduction)
  - Eliminated 13 global variables through class encapsulation
  - Implemented modular `lib/protocol/` and `lib/core/` structure
  - Fixed locomotive loading regression and button functionality
  - Added comprehensive debug logging with control flags

---

## KRITISCHE VERBESSERUNGEN (Dringlichkeit: HOCH)

### 1. Speicher-Management und Performance
- [x] **1.1** ✅ Aufteilen von `rocrail_controller.py` (26KB → 11KB) in kleinere Module
  - [x] RocrailProtocol Klasse erstellen (`lib/protocol/rocrail_protocol.py`) - 148 Zeilen
  - [x] ControllerStateMachine Klasse erstellen (`lib/core/controller_state.py`) - 78 Zeilen  
  - [x] Main Controller refactored (~700 → ~320 Zeilen)
  - [x] 13 globale Variablen eliminiert durch Klassen-Kapselung
  - [x] Callback-Mechanismus für Display-Updates implementiert
  - [x] Debug-Logging mit Kontrollflag hinzugefügt
  - **Status**: ✅ Completed (2025-08-04)
  - **Actual Effort**: 6 Stunden
  - **Priority**: Critical
  - **Benefits**: Bessere Testbarkeit, klare Verantwortlichkeiten, modulare Wartung

- [ ] **1.2** Globale Variablen durch Klassen-basierte Architektur ersetzen
  - [x] ~~13 kritische globale Variablen eliminiert~~ (durch Task 1.1 erledigt)
  - [ ] MainController Klasse mit Zustandsverwaltung (optional)
  - [ ] Dependency Injection für Hardware-Komponenten (optional)
  - **Status**: Partially Completed by Task 1.1
  - **Dependencies**: ~~Task 1.1~~ ✅ Completed
  - **Estimated Effort**: 1 Stunde (verringert)
  - **Priority**: Low (reduziert durch Task 1.1)

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
- [x] **4.1** ✅ Einheitliche Hardware-Konfiguration
  - [x] `btn_config.py` und `rocrail_config.py` zusammengeführt
  - [x] Neue `hardware_config.py` für Pin-Definitionen und LED-Zuordnungen
  - [x] Neue `config.py` für Anwendungseinstellungen (WiFi, RocRail, Timing)
  - [x] WiFi-Config-Server NeoPixel-Konflikt behoben (6→10 LEDs)
  - [x] Boot.py Bug behoben (green_button Check korrigiert)
  - [x] Alle Imports erfolgreich migriert
  - **Status**: ✅ Completed (2025-08-04)
  - **Actual Effort**: 2 Stunden
  - **Priority**: Medium
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
- [x] **8.1** ✅ Lange Funktionen aufteilen (teilweise durch Task 1.1)
  - [x] ~~`handle_data()` Funktion refactoren~~ → `RocrailProtocol.handle_data()`
  - [x] ~~Socket-Management extrahieren~~ → `RocrailProtocol` Klasse
  - [x] ~~State-Management extrahieren~~ → `ControllerStateMachine` Klasse
  - [ ] Main loop in State Pattern umwandeln (optional)  
  - [x] Funktionen unter 50 Zeilen halten (größtenteils erfüllt)
  - **Status**: ✅ Mostly Completed (durch Task 1.1)
  - **Actual Effort**: 2 Stunden (durch Task 1.1)

- [x] **8.2** ✅ Code-Dokumentation verbessern (teilweise durch Task 1.1)
  - [x] ~~README_DEVELOPMENT.md aktualisieren~~ → Neue Architektur dokumentiert
  - [x] Docstrings für neue Klassen (`RocrailProtocol`, `ControllerStateMachine`)
  - [ ] Docstrings für alle verbleibenden öffentlichen Methoden
  - [ ] Inline-Kommentare für komplexe Logik
  - **Status**: ✅ Partially Completed (durch Task 1.1)
  - **Actual Effort**: 1 Stunde (durch Task 1.1)
  - **Remaining Effort**: 1 Stunde

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
- [x] **11.1** ✅ Module-Struktur implementieren (teilweise durch Task 1.1)
```
lib/
├── hardware/          # Hardware-abstraction
│   ├── neopixel_controller.py ✅
│   ├── button_controller.py ✅ 
│   └── poti_controller.py ✅
├── protocol/          # Communication protocols ✅ NEW
│   ├── rocrail_protocol.py ✅ NEW
│   └── xml_builder.py (geplant)
├── controllers/       # Business logic controllers (geplant)
│   ├── locomotive_controller.py
│   └── wifi_controller.py  
└── core/             # Core system components ✅ NEW
    ├── controller_state.py ✅ NEW (state management)
    ├── logger.py (geplant)
    └── config_manager.py (geplant)
```
- **Status**: ✅ Partially Completed (durch Task 1.1)
- **Actual Effort**: 2 Stunden (durch Task 1.1)
- **Remaining**: XML-Builder, WiFi-Controller, Logger, Config-Manager

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

### ✅ Speicher-Management und Performance (2025-08-04)
- [x] **Task 1.1**: Modular Architecture Implementation
  - [x] `rocrail_controller.py` von 26KB auf 11KB reduziert (~700 → ~320 Zeilen)
  - [x] `RocrailProtocol` Klasse (`lib/protocol/rocrail_protocol.py`) - TCP/XML-Kommunikation
  - [x] `ControllerStateMachine` Klasse (`lib/core/controller_state.py`) - Zustandsverwaltung  
  - [x] 13 globale Variablen durch Klassen-Kapselung eliminiert
  - [x] Callback-Mechanismus für UI-Updates implementiert
  - [x] Locomotive Loading von RocRail-Server wiederhergestellt
  - [x] Debug-Logging mit Kontrollflag für bessere Wartbarkeit
  - [x] README_DEVELOPMENT.md aktualisiert mit neuer Architektur

---

## NOTES & DECISIONS

### Design Decisions
- **MicroPython Compatibility**: Alle Lösungen müssen MicroPython-kompatibel sein
- **Memory Constraints**: ESP32 hat begrenzte RAM-Ressourcen
- **Battery Operation**: Code muss energie-effizient sein
- **Real-time Requirements**: Steuerungsbefehle müssen schnell übertragen werden

### Technical Debt
- ~~Große `rocrail_controller.py` Datei macht Wartung schwierig~~ ✅ **BEHOBEN** (Task 1.1)
- ~~Globale Variablen erschweren Testing und Debugging~~ ✅ **BEHOBEN** (Task 1.1) 
- ~~Hardware-Konfiguration verteilt auf 2 Dateien mit Konflikten~~ ✅ **BEHOBEN** (Task 4.1)
- Manueller XML-String-Bau ist fehleranfällig (→ Task 5.1: XML-Builder)
- Socket-Verbindung könnte stabiler sein (→ Tasks 2.1, 2.2)
- Keine strukturierte Error-Recovery (→ Task 7.1)

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
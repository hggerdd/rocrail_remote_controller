# ESP32 Locomotive Controller - Development Guide

## Project Overview

MicroPython ESP32 locomotive controller for Rocrail model railway systems. Battery-powered handheld device with 10 status LEDs, potentiometer speed control, and multiple buttons.

**Operating Modes:**
- **Configuration Mode**: Web server for WiFi/Rocrail setup (red button at boot)
- **Controller Mode**: Active locomotive control (default)

## Core Files Structure

### Critical Files
- `rocrail_controller.py` - Main control loop and WiFi management (~320 lines, refactored)
- `lib/protocol/rocrail_protocol.py` - RocRail TCP/XML protocol communication
- `lib/core/controller_state.py` - System state management and safety logic
- `lib/neopixel_controller.py` - 10 LED status visualization controller
- `config.py` - Application configuration (WiFi, RocRail, timing intervals)
- `hardware_config.py` - Hardware pin definitions and LED assignments

### Important Libraries (`lib/`)
- `loco_list.py` - Locomotive management (selection, XML parsing)
- `button_controller.py` - Debounced button input
- `poti_controller.py` - Filtered potentiometer reading
- `interval_timer.py` - Non-blocking timing utilities

### Web Interface (`frontend/`)
- `index.html`, `app.js`, `style.css` - Configuration web interface
- `wifi_config_server.py` - Configuration mode web server

## Hardware Configuration

### Physical LED Layout (10 NeoPixels)
- **LED 0**: WiFi symbol - WiFi connection status
- **LED 1**: "RR" text - RocRail connection status  
- **LED 2**: "<" symbol - Direction indicator (forward/true)
- **LED 3**: ">" symbol - Direction indicator (reverse/false)
- **LED 4**: No text - Activity indicator
- **LEDs 5-9**: Numbers "1-5" - Locomotive selection

### LED Status Logic
```python
# LED assignments from hardware_config.py
LED_WIFI = 0          # WiFi status
LED_ROCRAIL = 1       # RocRail connection ("RR")
LED_DIR_LEFT = 2      # Direction "<" (true)
LED_DIR_RIGHT = 3     # Direction ">" (false)  
LED_ACTIVITY = 4      # Activity indicator
LED_LOCO_START = 5    # First locomotive (LEDs 5-9)
```

**LED 0 (WiFi)**: Green blink (connected), Red blink (disconnected)
**LED 1 (RocRail)**: Orange (disconnected), Blink orange (connecting), Green (connected), Red (lost)
**LEDs 2-3 (Direction)**: Yellow when active direction, off when inactive
**LED 4 (Activity)**: Red blink when inactive (poti=0), off when active
**LEDs 5-9 (Locos)**: Blue for selected locomotive, all others off (energy saving)

### Button Configuration
```python
# From hardware_config.py
BTN_NOTHALT = 17          # Red emergency/config button
BTN_RICHTUNGSWECHEL = 19  # Green direction toggle
BTN_GELB = 22             # Yellow sound/horn
BTN_BLAU = 23             # Blue light toggle
BTN_MITTE_UP = 18         # Black up - next locomotive
BTN_MITTE_DOWN = 21       # Black down - previous locomotive
ADC_GESCHWINDIGKEIT = 34  # Speed potentiometer
```

## Communication Protocol

**RocRail XML Commands** (TCP socket):
```xml
<!-- Speed Control -->
<xmlh><xml size="35"/></xmlh><lc id="BR103" V="50" dir="true"/>
<!-- Light Control -->  
<xmlh><xml size="28"/></xmlh><fn id="BR103" fn0="true"/>
```

**Connection Status Tracking**:
- Monitors both successful sends and received data
- Status updates on socket errors or server disconnection
- Automatic recovery when communication resumes

## Key Development Areas

### Core Architecture (`lib/protocol/`, `lib/core/`)
- `RocrailProtocol` - TCP socket management, XML message creation/parsing, connection monitoring
- `ControllerStateMachine` - WiFi/RocRail/speed states, safety mechanisms, event coordination
- Modular design enables better testing and maintenance

### NeoPixel Control (`lib/neopixel_controller.py`)
- `wifi_status_led()` - WiFi connection blinking
- `rocrail_status_led()` - RocRail 4-state status  
- `direction_indicator_leds()` - Direction arrows
- `activity_indicator_led()` - Activity monitoring
- `update_locomotive_display()` - Loco selection (LEDs 5-9)

### Main Control Loop (`rocrail_controller.py`)
- WiFi management with robust reconnection and interface reset
- Hardware controller integration (buttons, potentiometer, LEDs)
- System orchestration using RocrailProtocol and ControllerStateMachine classes
- Timing-based event processing with safety mechanisms

### Configuration (`config.py` + `hardware_config.py`)
- WiFi credentials and RocRail server settings (`config.py`)
- Timing intervals and locomotive management settings (`config.py`)
- Hardware pin assignments and LED mappings (`hardware_config.py`)
- WiFi reconnection parameters and recovery settings (`config.py`)

## Development Commands

### Buffer Management Important Notes
**CRITICAL**: XML buffer management requires minimum buffer sizes:
- **Minimum buffer size: 4096 bytes** - smaller buffers cause parsing failures
- Buffer truncation must preserve complete XML structures when possible
- After locomotive loading: clear buffer regularly to prevent memory leaks
- Monitor memory usage: ESP32 crashes when free memory drops below ~10KB

### Commit Message Format
Always create precise, descriptive commit messages:
```
feat: Add new functionality
fix: Correct existing issue  
refactor: Code restructure without behavior change
docs: Documentation updates
```

### README Maintenance
Update `README_DEVELOPMENT.md` when:
- Adding new hardware features or LED functions
- Changing core system behavior or architecture
- Learning new project requirements or constraints
- Modifying file structure or critical dependencies

### Common Tasks
**Adding LED Functions**: Update `neopixel_controller.py` methods and `hardware_config.py` constants
**Button Integration**: Add to `hardware_config.py`, create `ButtonController` in main loop
**XML Commands**: Implement in send functions with error handling and status updates

## Current Status
- Modular architecture implemented: `RocrailProtocol` and `ControllerStateMachine` classes
- Main controller reduced from ~700 to ~320 lines through code extraction
- 10 LED system fully implemented with physical labels
- RocRail connection tracking via send/receive monitoring  
- Direction indicators synchronized with locomotive state
- Energy-efficient locomotive display (only selected LED active)
- Robust error handling and automatic recovery
- Advanced WiFi management with interface reset and graceful recovery from internal errors

Focus development on `lib/protocol/rocrail_protocol.py` for communication logic, `lib/core/controller_state.py` for state management, and `rocrail_controller.py` for system orchestration.

## Development Planning
See `TASKS.md` for comprehensive task list, priorities, and development roadmap. Tasks are categorized by urgency (Critical/Medium/Low) with effort estimates and dependencies tracked.
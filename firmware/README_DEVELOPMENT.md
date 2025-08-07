# ESP32 Locomotive Controller - Development Guide

## Project Overview

MicroPython ESP32 locomotive controller for Rocrail model railway systems. Battery-powered handheld device with 10 status LEDs, potentiometer speed control, and multiple buttons.

**MAJOR UPDATE: AsyncIO Implementation**
New asyncio-based implementation (`rocrail_controller_asyncio.py`) replaces polling-based architecture with event-driven async tasks. Better resource utilization, structured concurrency, eliminates global variables.

**Operating Modes:**
- **Configuration Mode**: Web server for WiFi/Rocrail setup (red button at boot)
- **Controller Mode**: Active locomotive control (default)

## Architecture Versions

### Legacy Implementation (`rocrail_controller.py`)
- Polling-based main loop with IntervalTimer
- Thread-based socket communication
- Global variables and shared state
- ~320 lines with modular design

### AsyncIO Implementation (`rocrail_controller_asyncio.py`)
- Event-driven async tasks
- AsyncIO socket communication
- Lock/Queue-based state management
- Structured concurrency with proper resource cleanup
- Eliminates timer-based polling loops

## AsyncIO Implementation Issues Resolved

**Critical Failures Encountered & Fixed:**

1. **`Error running main rocrail_controller.py: Queue`**
   - **Cause**: `asyncio.Queue` not available in MicroPython asyncio
   - **Solution**: Replaced with `list + asyncio.Event` in `async_protocol.py`
   - **Files**: `lib/async_controllers/async_protocol.py`

2. **`'Stream' object has no attribute 'is_closing'`**
   - **Cause**: MicroPython StreamWriter lacks `is_closing()` method
   - **Solution**: Use `hasattr(writer, 'write')` for connection checks
   - **Files**: `lib/async_controllers/async_protocol.py`

3. **`StreamWriter.wait_closed()` compatibility**  
   - **Cause**: Method may not exist in all MicroPython versions
   - **Solution**: Wrapped with `hasattr()` check and try/except
   - **Files**: `lib/async_controllers/async_protocol.py`

4. **Buttons not working**
   - **Cause**: Over-complex debouncing logic with multiple negations
   - **Solution**: Simplified to direct 1→0 transition detection (pull-up)  
   - **Files**: `lib/async_controllers/async_hardware.py`

5. **Potentiometer limited range**
   - **Cause**: Missing mechanical calibration (1310-2360 → 0-100 mapping)
   - **Solution**: Added `_normalize_speed()` with proper calibration
   - **Files**: `lib/async_controllers/async_hardware.py`

6. **Event loop compatibility**
   - **Cause**: `asyncio.run()` not available in older MicroPython
   - **Solution**: Fallback to `get_event_loop().run_until_complete()`
   - **Files**: `rocrail_controller_asyncio.py`

7. **Time function compatibility**
   - **Cause**: `time.time()` less precise than MicroPython alternatives
   - **Solution**: Use `time.ticks_ms()` and `time.ticks_diff()`
   - **Files**: `lib/async_controllers/async_wifi.py`

**Prevention**: Run `python test_full_compatibility.py` before deployment to catch these issues early.

## AsyncIO Benefits

**Structured Concurrency:**
- Replace timer loops with async tasks
- Proper resource management and cleanup
- Better error handling and recovery
- Event-driven instead of polling

**Resource Optimization:**
- Single event loop instead of multiple threads
- Reduced memory overhead
- Better CPU utilization
- Cleaner state management with locks/queues

**Maintainability:**
- No global variables - state managed by async primitives
- Clear task separation and responsibilities  
- Easier testing and debugging
- Modular component design

**MicroPython AsyncIO Compatibility Issues & Solutions:**

⚠️ **Common AsyncIO Pitfalls** - Issues encountered and solved in this implementation:

1. **`asyncio.Queue` not available** → Use `list + asyncio.Event`
   ```python
   # ❌ Fails in MicroPython
   queue = asyncio.Queue()
   
   # ✅ MicroPython compatible
   queue = []
   queue_event = asyncio.Event()
   ```



9. **Boot LED indicators with asyncio** ✅ **RESOLVED**
   - **Cause**: AsyncNeoPixelController requires event loop, not available in boot.py
   - **Solution**: Direct NeoPixel control in boot.py before asyncio initialization
   - **Files**: `boot.py`
   - **Indicators**: Orange (boot), Purple (config mode), Green (normal operation)

10. **AsyncIO LED startup delay** ✅ **RESOLVED** 
   - **Cause**: LED update task waited for complete initialization before starting
   - **Solution**: LED task starts immediately after hardware init, during WiFi/RocRail connection
   - **Files**: `rocrail_controller_asyncio.py`, `async_leds.py`
   - **Result**: Instant LED feedback during connection attempts, no more ~30s delay
   - **Architecture**: LED task launches in `initialize()` before network connections
2. **`writer.is_closing()` method missing** → Use `hasattr()` checks
   ```python
   # ❌ Fails: 'Stream' object has no attribute 'is_closing'
   if not writer.is_closing():
   
   # ✅ MicroPython compatible  
   if writer and hasattr(writer, 'write'):
   ```

3. **`writer.wait_closed()` may not exist** → Wrap with compatibility check
   ```python
   # ✅ Safe approach
   if hasattr(writer, 'wait_closed'):
       try:
           await writer.wait_closed()
       except:
           pass
   ```

4. **`asyncio.wait_for()` missing** → Add fallback
   ```python
   # ✅ With fallback
   if hasattr(asyncio, 'wait_for'):
       result = await asyncio.wait_for(operation(), timeout=10)
   else:
       result = await operation()  # No timeout
   ```

5. **`asyncio.gather()` unreliable** → Use individual task monitoring
   ```python
   # ❌ May fail with long-running tasks
   await asyncio.gather(*tasks)
   
   # ✅ Individual monitoring
   while tasks:
       await asyncio.sleep(1)
       # Check and handle completed tasks
   ```

6. **`asyncio.run()` not available** → Event loop fallback
   ```python
   # ✅ Compatible approach
   if hasattr(asyncio, 'run'):
       asyncio.run(main())
   else:
       loop = asyncio.get_event_loop()
       loop.run_until_complete(main())
   ```

7. **Complex button debouncing fails** → Simplify logic
   ```python
   # ✅ Direct transition detection (pull-up)
   if last_state == 1 and current_state == 0:
       return True  # Button pressed
   ```

8. **Missing hardware calibration** → Always migrate hardware-specific code
   - Potentiometer ranges, LED brightness, timing constants
   - Don't assume linear mappings work for all hardware

**Testing Strategy**: Always test with actual MicroPython before deployment:
```bash
python test_full_compatibility.py  # Comprehensive compatibility check
```

**📋 For Future AsyncIO Development**: 
- `MICROPYTHON_ASYNCIO_CHECKLIST.md` - Complete compatibility checklist
- `ASYNCIO_ISSUES_RESOLVED.md` - Summary of all issues fixed
- Use these guides to prevent the same compatibility issues in future implementations

**Testing:**
```python
# Test basic asyncio compatibility
python test_basic_asyncio.py

# Test stream operations compatibility  
python test_stream_compatibility.py

# Test button functionality
python test_raw_buttons.py         # Raw pin monitoring
python test_minimal_buttons.py     # AsyncIO hardware manager test
python test_buttons_asyncio.py     # Full button test with poti

# Test potentiometer calibration
python test_poti_calibration.py    # Potentiometer range and calibration

# Run asyncio controller
python rocrail_controller_asyncio.py

# Full component tests
python test_asyncio.py
```

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

**LED 0 (WiFi)**: Green (bright/dim pulse when connected), Orange (bright/dim blink when connecting), Red (bright/dim blink when failed)
**LED 1 (RocRail)**: Solid green (connected), Orange bright/dim blink (connecting), Red-orange fast bright/dim (reconnecting), Solid red (lost)
**LEDs 2-3 (Direction)**: Bright yellow for active direction, off for inactive
**LED 4 (Activity)**: Purple bright/dim blink when poti zero required, off when normal
**LEDs 5-9 (Locos)**: Bright blue for selected locomotive, off for others (energy saving)

**Brightness Levels** (configurable in `lib/neopixel_controller.py`):
- `LED_BRIGHT = 255` - Full brightness for active/on states
- `LED_DIM_HIGH = 50` - Medium dim for connected states  
- `LED_DIM_LOW = 20` - Low dim for "off" phase of blinking
- `LED_DIM_MIN = 10` - Minimum brightness (currently unused)

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

### Potentiometer Calibration
**Physical Range Limitation**: Due to mechanical constraints, the potentiometer cannot use the full ADC range (0-4095).
**Calibrated Range**: 1310-2360 (from adc_test.py measurements)
**Output Mapping**: Calibrated range mapped to 0-100 locomotive speed
**Testing**: Use `python test_poti_calibration.py` to verify calibration accuracy

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
- `RocrailProtocol` - TCP socket management, XML message creation/parsing, connection monitoring, **robust auto-reconnection with fast retry logic**
- `ControllerStateMachine` - WiFi/RocRail/speed states, safety mechanisms, event coordination
- Modular design enables better testing and maintenance

### NeoPixel Control (`lib/neopixel_controller.py`)
- Simple, reliable LED control with configurable brightness levels
- `wifi_status_led()` - WiFi status with dim/bright states instead of on/off
- `rocrail_status_led()` - RocRail connection with smooth brightness transitions
- `direction_indicator_leds()` - Direction arrows (yellow)
- `poti_zero_request_led()` - Purple dim/bright when poti reset needed
- `update_locomotive_display()` - Blue LED for selected loco
- **Brightness Configuration**: Adjustable LED_BRIGHT/LED_DIM values at top of file
- **Smooth Blinking**: Uses brightness variation instead of on/off for better visibility
- **Energy Efficient**: Dim states reduce power consumption while maintaining visibility

### Main Control Loop (`rocrail_controller.py`)
- WiFi management with robust reconnection and interface reset
- Hardware controller integration (buttons, potentiometer, LEDs)
- System orchestration using RocrailProtocol and ControllerStateMachine classes
- Timing-based event processing with safety mechanisms
- **Startup stabilization**: 3-second delay after socket connection prevents thread race conditions

### Configuration (`config.py` + `hardware_config.py`)
- WiFi credentials and RocRail server settings (`config.py`)
- Timing intervals and locomotive management settings (`config.py`)
- Hardware pin assignments and LED mappings (`hardware_config.py`)
- WiFi reconnection parameters and recovery settings (`config.py`)

## Common Issues & Solutions

### Startup Lockup Fix (~50% failure rate)
**Problem**: System hangs in ~50% of startups, especially in first 3 seconds
**Solution**: 
- Extended startup stabilization to 3 seconds with 100ms NeoPixel refresh intervals
- Added periodic NeoPixel refresh every 2 seconds in main loop
- _write2() method for alternative LED write without state change
- refresh() method called periodically to prevent RMT lockups

### WiFi Connection Delay
**Problem**: Long delay between connection and green WiFi LED
**Solution**:
- Optimized serial output (compact messages, fewer characters)
- Reduced verbose debug messages
- Faster status updates with emoji/symbol indicators

### NeoPixel Simplified Design
**Previous Issues**: Complex RMT error recovery caused code bloat
**Current Solution**: Simplified controller with silent error handling
- **Minimal Error Handling**: Write errors silently ignored
- **Clean Code**: Removed complex recovery mechanisms
- **Reliable Operation**: Basic functionality prioritized
- **Fast Response**: No delays or recovery attempts
- **Fallback**: Controller continues if LEDs fail
- **Stability Workaround**: Added _write2() and refresh() methods for periodic NeoPixel refresh
- **Startup Protection**: 3-second stabilization with 100ms refresh intervals prevents early lockups

**Hardware Notes**:
- Uses pin 5 for NeoPixel data (10 LEDs)
- Alternative pins if needed: 25, 26, 27
- Disable with: `neopixel_ctrl.force_disable()`
- Call `neopixel_ctrl.refresh()` every 2 seconds in main loop for stability

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
- Modular architecture: `RocrailProtocol` and `ControllerStateMachine` classes
- **Robust auto-reconnection**: Fast retry logic, unlimited attempts
- Main controller maintained at ~320 lines through modular design
- **Simplified NeoPixel**: Clean implementation with periodic refresh for stability
- 10 LED system with physical labels, status visualization
- RocRail connection tracking via send/receive monitoring  
- Direction indicators synchronized with locomotive state
- Energy-efficient locomotive display (only selected LED active)
- Advanced WiFi management with interface reset capability
- **Startup stabilization**: 3-second delay with NeoPixel refresh prevents race conditions
- **Reliable LED control**: Simplified error handling with periodic refresh for stability
- **Compact debug output**: Minimized serial output for better performance

Focus: `lib/protocol/rocrail_protocol.py` for communication, `lib/core/controller_state.py` for state management, `rocrail_controller.py` for orchestration.

## Development Planning
See `TASKS.md` for comprehensive task list, priorities, and development roadmap. Tasks are categorized by urgency (Critical/Medium/Low) with effort estimates and dependencies tracked.
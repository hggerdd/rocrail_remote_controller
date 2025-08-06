import network
import time
import machine
from machine import Pin

from config import *
from hardware_config import *
from lib.interval_timer import IntervalTimer
from lib.poti_controller import PotiController
from lib.button_controller import ButtonController
from lib.neopixel_controller import NeoPixelController
from lib.loco_list import LocoList
from lib.protocol.rocrail_protocol import RocrailProtocol
from lib.core.controller_state import ControllerStateMachine

# WiFi interface
wlan = None

# Initialize locomotive management
loco_list = LocoList(LOCO_LIST_FILE)
loco_dir = "true"
loco_light = "false"

# Initialize hardware controllers
speed_poti = PotiController(pin_num=ADC_GESCHWINDIGKEIT, filter_size=5, threshold=1)
light_button = ButtonController(pin_num=BTN_BLAU, debounce_ms=5)
emergency_button = ButtonController(pin_num=BTN_NOTHALT, debounce_ms=5)
direction_button = ButtonController(pin_num=BTN_RICHTUNGSWECHEL, debounce_ms=5)
sound_button = ButtonController(pin_num=BTN_GELB, debounce_ms=5)

# Locomotive selection buttons
btn_up = ButtonController(pin_num=BTN_MITTE_UP, debounce_ms=5)
btn_down = ButtonController(pin_num=BTN_MITTE_DOWN, debounce_ms=5)

# Initialize NeoPixel controller - turns off all LEDs at startup
try:
    neopixel_ctrl = NeoPixelController(pin_num=NEOPIXEL_PIN, num_leds=NEOPIXEL_COUNT)
    print("[STARTUP] NeoPixel controller initialized successfully")
except Exception as e:
    print(f"[STARTUP] NeoPixel initialization failed: {e}")
    print("[STARTUP] Creating dummy NeoPixel controller - LEDs disabled")
    # Create a dummy controller that does nothing
    class DummyNeoPixelController:
        def is_enabled(self): return False
        def all_off(self): pass
        def wifi_status_led(self, *args): pass
        def rocrail_status_led(self, *args): pass
        def direction_indicator_leds(self, *args): pass
        def poti_zero_request_led(self, *args): pass
        def update_locomotive_display(self, *args): pass
        def clear_locomotive_display(self): pass
        def force_disable(self): pass
    neopixel_ctrl = DummyNeoPixelController()

def update_locomotive_display():
    """Update NeoPixel display to show current locomotive selection"""
    try:
        selected_index = loco_list.get_selected_index()
        total_locos = loco_list.get_count()
        if neopixel_ctrl.is_enabled():
            neopixel_ctrl.update_locomotive_display(selected_index, total_locos)
        print(loco_list.get_status_string())
    except Exception as e:
        print(f"[ERROR] Exception in locomotive display update: {e}")
        if neopixel_ctrl:
            neopixel_ctrl.force_disable()

# Initialize protocol and state management
print("[LOCO_DEBUG] Initializing RocrailProtocol with locomotive list and display callback...")
rocrail_protocol = RocrailProtocol(loco_list, update_locomotive_display)
state_machine = ControllerStateMachine()
print(f"[LOCO_DEBUG] RocrailProtocol initialized - callback set: {rocrail_protocol.display_update_callback is not None}")

# Set initial LED states before any connections
try:
    if neopixel_ctrl.is_enabled():
        # WiFi indicator: initial orange (before attempting connection)
        neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status())
        # RocRail indicator: disconnected state
        neopixel_ctrl.rocrail_status_led(rocrail_protocol.get_status())
        # Clear all other LEDs
        neopixel_ctrl.clear_locomotive_display()
        print("[STARTUP] Initial LED states set")
    else:
        print("[STARTUP] LEDs disabled - skipping initial LED setup")
except Exception as e:
    print(f"[STARTUP] Initial LED setup failed: {e}")
    neopixel_ctrl.force_disable()

def reset_wifi_interface():
    """Reset WiFi interface to recover from internal errors"""
    global wlan
    
    try:
        print("Resetting WiFi interface...")
        if wlan:
            wlan.disconnect()
            wlan.active(False)
            time.sleep(1)  # Wait for cleanup
        
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        time.sleep(0.5)  # Wait for activation
        print("WiFi interface reset complete")
        return True
    except Exception as e:
        print(f"WiFi interface reset failed: {e}")
        return False

def connect_wifi(ssid, password, state_machine, max_retries=10):
    global wlan
    
    # Set connecting status
    state_machine.set_wifi_status("connecting")
    
    # Create WLAN interface if not exists
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    
    try:
        # Activate the interface
        wlan.active(True)
        time.sleep(0.2)  # Wait for activation
        
        # Check if already connected
        if wlan.isconnected():
            print("Already connected to WiFi")
            print("Network config:", wlan.ifconfig())
            state_machine.set_wifi_status("connected")
            return True
        
        # Connect to WiFi with error handling
        print(f"Connecting to {ssid}...")
        try:
            wlan.connect(ssid, password)
        except Exception as e:
            print(f"WiFi connect error: {e}")
            # Try to reset interface and retry once
            if reset_wifi_interface():
                try:
                    wlan.connect(ssid, password)
                except Exception as e2:
                    print(f"WiFi connect retry failed: {e2}")
                    state_machine.set_wifi_status("failed")
                    return False
            else:
                state_machine.set_wifi_status("failed")
                return False
        
        # Wait for connection with timeout and blink LED
        retry_count = 0
        blink_toggle = False
        last_blink_time = time.ticks_ms()
        last_retry_time = time.ticks_ms()
        
        while not wlan.isconnected() and retry_count < max_retries:
            current_time = time.ticks_ms()
            
            # Blink the LED every 500ms during connection
            if time.ticks_diff(current_time, last_blink_time) >= NEOPIXEL_BLINK_INTERVAL:
                blink_toggle = not blink_toggle
                try:
                    if neopixel_ctrl.is_enabled():
                        neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status(), blink_toggle)
                except Exception as e:
                    print(f"[ERROR] WiFi connect LED blink failed: {e}")
                    neopixel_ctrl.force_disable()
                last_blink_time = current_time
            
            # Check connection more frequently than before
            time.sleep(0.1)
            
            # Increment retry counter every second
            if time.ticks_diff(current_time, last_retry_time) >= 1000:
                print("Waiting for connection...")
                retry_count += 1
                last_retry_time = current_time
        
        # Check connection status
        if wlan.isconnected():
            print("Connected to WiFi")
            print("Network config:", wlan.ifconfig())
            state_machine.set_wifi_status("connected")
            return True
        else:
            print("Failed to connect")
            state_machine.set_wifi_status("failed")
            return False
            
    except Exception as e:
        print(f"WiFi connection error: {e}")
        state_machine.set_wifi_status("failed")
        return False

def reconnect_wifi(state_machine):
    """Robust WiFi reconnection with interface reset if needed"""
    global wlan
    
    print("WiFi reconnection starting...")
    
    # First try simple reconnection
    if connect_wifi(WIFI_SSID, WIFI_PASSWORD, state_machine, max_retries=3):
        return True
    
    # If that fails, reset interface and try again
    print("Simple reconnection failed, resetting interface...")
    if reset_wifi_interface():
        if connect_wifi(WIFI_SSID, WIFI_PASSWORD, state_machine, max_retries=WIFI_RECONNECT_MAX_RETRIES):
            return True
    
    print("WiFi reconnection failed after interface reset")
    return False

def handle_locomotive_selection(state_machine, rocrail_protocol):
    """Handle locomotive selection button presses"""
    selection_changed = False
    
    # Handle UP button (next locomotive)
    if btn_up.is_pressed():
        if loco_list.select_next():
            selection_changed = True
            print("Selected next locomotive")
    
    # Handle DOWN button (previous locomotive)
    if btn_down.is_pressed():
        if loco_list.select_previous():
            selection_changed = True
            print("Selected previous locomotive")
    
    # Update display if selection changed
    if selection_changed:
        update_locomotive_display()
        # Update direction indicator LEDs for new locomotive
        try:
            if neopixel_ctrl.is_enabled():
                neopixel_ctrl.direction_indicator_leds(loco_dir == "true")
        except Exception as e:
            print(f"[ERROR] Direction LED update in selection failed: {e}")
            neopixel_ctrl.force_disable()
        # Reset speed sending to ensure new locomotive starts safely
        state_machine.handle_locomotive_change()
        rocrail_protocol.send_speed_and_direction(0, loco_dir)
        print("Locomotive changed - POTI ZERO REQUIRED (purple LED blinking)")

def initialize_locomotive_list(rocrail_protocol):
    """Initialize locomotive list - load from file and query from RocRail for updates"""
    
    if loco_list.get_count() == 0:
        # No locomotives loaded, add default
        print("No saved locomotives - adding default and querying RocRail...")
        loco_list.add_locomotive(DEFAULT_LOCO_ID)
        loco_list.save_to_file()
    else:
        print(f"Loaded {loco_list.get_count()} locomotives from file")
    
    # Always query RocRail for latest locomotive list (don't set locomotives_loaded=True from file)
    print("Querying RocRail for current locomotive list...")
    rocrail_protocol.query_locomotives()
    
    # Update display with current locomotives (from file or default)
    update_locomotive_display()

# Main program
run = True
if run:    
    # Connect to WiFi with robust reconnection
    print("Starting WiFi connection...")
    if connect_wifi(WIFI_SSID, WIFI_PASSWORD, state_machine):
        print("WiFi connection successful")
        
        # initialize the timer for regular events
        timer = IntervalTimer()
        
        # Connect to the rocrail server and start background monitoring
        print("connect to " + ROCRAIL_HOST)
        if rocrail_protocol.start_connection(ROCRAIL_HOST, ROCRAIL_PORT, rocrail_protocol.handle_data):
            
            # Initialize locomotive list
            initialize_locomotive_list(rocrail_protocol)
            
            # Initialize direction indicator LEDs with current direction
            try:
                if neopixel_ctrl.is_enabled():
                    neopixel_ctrl.direction_indicator_leds(loco_dir == "true")
                    print("[STARTUP] Direction LEDs initialized")
            except Exception as e:
                print(f"[STARTUP] Direction LED initialization failed: {e}")
                neopixel_ctrl.force_disable()
            
            # SIMPLE STARTUP STABILIZATION: Short delay for thread stabilization
            print("System startup - waiting 3 seconds for socket stabilization...")
            time.sleep(3.0)
            print("Startup stabilization complete - system ready")
            
            # Initialise speed values
            last_speed = -1
            speed = 0
            
            # Initialize WiFi status blinking
            wifi_blink_toggle = False
            rocrail_blink_toggle = False
            
            try:
                # Main program loop
                while True:
                    
                    # Check for locomotive query timeout (only if still loading locomotives)
                    if not rocrail_protocol.are_locomotives_loaded() and rocrail_protocol.is_query_pending() and rocrail_protocol.get_query_start_time() > 0:
                        if time.ticks_diff(time.ticks_ms(), rocrail_protocol.get_query_start_time()) > LOCO_QUERY_TIMEOUT:
                            print("[LOCO_DEBUG] Locomotive query timeout - no response received")
                            print(f"[LOCO_DEBUG] Timeout after {LOCO_QUERY_TIMEOUT}ms, resetting query state")
                            rocrail_protocol.reset_query_state()
                    
                    # Memory monitoring every 30 seconds
                    if timer.is_ready("memory_check", 30000):
                        try:
                            import gc
                            gc.collect()
                            free_mem = gc.mem_free()
                            allocated_mem = gc.mem_alloc()
                            print(f"[MEMORY] Free: {free_mem}B, Allocated: {allocated_mem}B")
                            if free_mem < 15000:  # Critical memory warning
                                print(f"[MEMORY] ⚠️  CRITICAL: Only {free_mem} bytes free!")
                                # Force aggressive garbage collection
                                gc.collect()
                                gc.collect()  # Double collection
                        except Exception as e:
                            print(f"[MEMORY] Error checking memory: {e}")
                    
                    if timer.is_ready("check_wifi_update", WIFI_CHECK_INTERVAL):
                        print("check wifi connection")
                        try:
                            if not wlan or not wlan.isconnected():
                                print("!!! wifi not connected --> reconnect")
                                # Update status to show we're trying to reconnect
                                if state_machine.get_wifi_status() != "connecting":
                                    state_machine.set_wifi_status("connecting")
                                # Attempt robust reconnection
                                if reconnect_wifi(state_machine):
                                    print("WiFi reconnection successful")
                                else:
                                    print("WiFi reconnection failed - continuing with recovery mode")
                                    state_machine.set_wifi_status("failed")
                            else:
                                # WiFi is connected, ensure status is correct
                                if state_machine.get_wifi_status() != "connected":
                                    state_machine.set_wifi_status("connected")
                                    print("WiFi status updated to connected")
                        except Exception as e:
                            print(f"WiFi check error: {e}")
                            state_machine.set_wifi_status("failed")
                            # Try to reset interface for next check
                            reset_wifi_interface()
                    
                    # Update WiFi and status LEDs (blinking) - REDUCED FREQUENCY to protect RMT
                    if timer.is_ready("neopixel_blink", NEOPIXEL_BLINK_INTERVAL * 2):  # Double interval = half frequency
                        try:
                            wifi_blink_toggle = not wifi_blink_toggle
                            rocrail_blink_toggle = not rocrail_blink_toggle
                            
                            # Skip LED updates if NeoPixel is disabled to prevent hangs
                            if neopixel_ctrl.is_enabled():
                                neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status(), wifi_blink_toggle)
                                neopixel_ctrl.rocrail_status_led(rocrail_protocol.get_status(), rocrail_blink_toggle)
                                neopixel_ctrl.poti_zero_request_led(not state_machine.is_speed_sending_enabled(), wifi_blink_toggle)
                            else:
                                # LEDs disabled - log periodically
                                if timer.is_ready("led_disabled_info", 15000):
                                    print("[LED] NeoPixel disabled - continuing without LED status")
                        except Exception as e:
                            print(f"[LED] Exception in LED updates - disabling LEDs: {e}")
                            neopixel_ctrl.force_disable()
                            print("[LED] LEDs permanently disabled due to errors")
                    
                    # Handle locomotive selection buttons
                    if timer.is_ready("check_loco_selection", BUTTON_CHECK_INTERVAL):
                        try:
                            handle_locomotive_selection(state_machine, rocrail_protocol)
                        except Exception as e:
                            print(f"[ERROR] Exception in locomotive selection: {e}")
                            import sys
                            sys.print_exception(e)
                    
                    # Query locomotives periodically only if we haven't loaded them yet
                    if not rocrail_protocol.are_locomotives_loaded() and timer.is_ready("query_locomotives", LOCO_QUERY_INTERVAL):
                        if not rocrail_protocol.is_query_pending():  # Only query if not already waiting for response
                            print("[LOCO_DEBUG] Periodic locomotive query - sending request...")
                            rocrail_protocol.query_locomotives()
                        else:
                            print(f"[LOCO_DEBUG] Locomotive query already pending (started: {rocrail_protocol.get_query_start_time()})")
                    
                    # regularly update the poti/button input controller (required to have enough values for mean)
                    if timer.is_ready("send_poti_update", POTI_UPDATE_INTERVAL):
                        try:
                            # update speed from poti position/angle
                            speed = speed_poti.read()
                            
                            # check direction button(incl. debouncing),
                            # toggle direction and set speed to 0,
                            # disable speed sending until the
                            # selection (poti) is set to speed 0
                            if direction_button.is_pressed():
                                print(f"[DEBUG] Direction button pressed")
                                loco_dir = "true" if loco_dir == "false" else "false"
                                rocrail_protocol.send_speed_and_direction(0, loco_dir)
                                state_machine.handle_direction_change()
                                # Update direction indicator LEDs
                                try:
                                    if neopixel_ctrl.is_enabled():
                                        neopixel_ctrl.direction_indicator_leds(loco_dir == "true")
                                except Exception as e:
                                    print(f"[ERROR] Direction LED update failed: {e}")
                                    neopixel_ctrl.force_disable()
                                print(f"Direction: {loco_dir} - POTI ZERO REQUIRED (purple LED blinking)")
                                
                            # check emergency button
                            if emergency_button.is_pressed():
                                print(f"[DEBUG] Emergency button pressed")
                                rocrail_protocol.send_speed_and_direction(0, loco_dir)
                                state_machine.handle_emergency_stop()
                                print("EMERGENCY STOP - POTI ZERO REQUIRED (purple LED blinking)")
                            
                            # Light button pressed, toggle the light
                            if light_button.is_pressed():
                                print(f"[DEBUG] Light button pressed")
                                loco_light = "true" if loco_light == "false" else "false"
                                rocrail_protocol.send_light_command(loco_light)
                                print(f"Light: {loco_light}")
                                
                            # Sound button pressed
                            if sound_button.is_pressed():
                                print(f"[DEBUG] Sound button pressed")
                                print("Horn activated")
                                
                        except Exception as e:
                            print(f"[ERROR] Exception in poti/button handling: {e}")
                            import sys
                            sys.print_exception(e)
                
                    # every SPEED_UPDATE_INTERVAL check if speed has changed and can be updated (avoid too many commands)
                    if timer.is_ready("update_speed", SPEED_UPDATE_INTERVAL):
                        try:
                            if state_machine.is_speed_sending_enabled():
                                if (speed != last_speed):
                                    print(f"Speed: {speed} (enabled: {state_machine.is_speed_sending_enabled()})")
                                    rocrail_protocol.send_speed_and_direction(speed, loco_dir)
                                    last_speed = speed
                            else:
                                state_machine.check_speed_enable_condition(speed)
                                if state_machine.is_speed_sending_enabled():
                                    print("Speed sending re-enabled - poti zero request cleared (purple LED off)")
                        except Exception as e:
                            print(f"[ERROR] Exception in speed handling: {e}")
                            import sys
                            sys.print_exception(e)                       
                    
                    # Periodic cleanup after locomotives are loaded (every 5 minutes)
                    if rocrail_protocol.are_locomotives_loaded() and timer.is_ready("periodic_cleanup", 300000):
                        try:
                            import gc
                            print("[CLEANUP] Performing periodic memory cleanup...")
                            # Force garbage collection
                            gc.collect()
                            gc.collect()  # Double collection for better results
                            free_mem = gc.mem_free()
                            print(f"[CLEANUP] Memory after cleanup: {free_mem} bytes free")
                        except Exception as e:
                            print(f"[CLEANUP] Error during cleanup: {e}")
                    
                    # Heartbeat every 5 seconds to show main loop is alive with detailed status
                    if timer.is_ready("heartbeat", 5000):
                        wifi_status = state_machine.get_wifi_status()
                        rocrail_status = rocrail_protocol.get_status()
                        leds_enabled = neopixel_ctrl.is_enabled() if neopixel_ctrl else False
                        led_recovery_count = neopixel_ctrl.recovery_attempts if hasattr(neopixel_ctrl, 'recovery_attempts') else 0
                        print(f"[HEARTBEAT] Loop alive - WiFi:{wifi_status} RocRail:{rocrail_status} LEDs:{leds_enabled} Recoveries:{led_recovery_count} Speed:{speed}")
                    
                    # Small delay to prevent CPU hogging
                    time.sleep(0.05)
                    
            except KeyboardInterrupt:
                print("Program interrupted")
                rocrail_protocol.stop_connection()
    else:
        print("WiFi connection failed")
        # WiFi status is already set to "failed" by connect_wifi function
        # Clear locomotive display
        try:
            if neopixel_ctrl.is_enabled():
                neopixel_ctrl.clear_locomotive_display()
        except Exception as e:
            print(f"[ERROR] LED clear failed: {e}")
            neopixel_ctrl.force_disable()
        
        # Keep trying to reconnect and blink red LED
        timer = IntervalTimer()
        wifi_blink_toggle = False
        
        try:
            while True:
                # Update WiFi status LED (blinking red)
                if timer.is_ready("neopixel_blink", NEOPIXEL_BLINK_INTERVAL):
                    wifi_blink_toggle = not wifi_blink_toggle
                    try:
                        if neopixel_ctrl.is_enabled():
                            neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status(), wifi_blink_toggle)
                    except Exception as e:
                        print(f"[ERROR] WiFi recovery LED update failed: {e}")
                        neopixel_ctrl.force_disable()
                
                # Try to reconnect WiFi periodically with robust method
                if timer.is_ready("wifi_reconnect", WIFI_CHECK_INTERVAL):
                    print("Attempting robust WiFi reconnection...")
                    if reconnect_wifi(state_machine):
                        print("WiFi reconnection successful - restarting main program")
                        machine.reset()  # Restart the program to enter normal operation
                        break
                    else:
                        print("WiFi reconnection still failed")
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("Program interrupted during WiFi recovery")
            
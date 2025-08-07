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

# Initialize NeoPixel controller
neopixel_ctrl = NeoPixelController(pin_num=NEOPIXEL_PIN, num_leds=NEOPIXEL_COUNT)
if not neopixel_ctrl.is_enabled():
    print("[!] NeoPixel disabled")

def update_locomotive_display():
    """Update NeoPixel display to show current locomotive selection"""
    selected_index = loco_list.get_selected_index()
    total_locos = loco_list.get_count()
    if neopixel_ctrl.is_enabled():
        neopixel_ctrl.update_locomotive_display(selected_index, total_locos)

# Initialize protocol and state management
rocrail_protocol = RocrailProtocol(loco_list, update_locomotive_display)
state_machine = ControllerStateMachine()

# Set initial LED states
if neopixel_ctrl.is_enabled():
    neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status())
    neopixel_ctrl.rocrail_status_led(rocrail_protocol.get_status())
    neopixel_ctrl.clear_locomotive_display()

def reset_wifi_interface():
    """Reset WiFi interface to recover from internal errors"""
    global wlan
    
    try:
        print("WiFi reset...")
        if wlan:
            wlan.disconnect()
            wlan.active(False)
            time.sleep(1)
        
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        time.sleep(0.5)
        print("WiFi reset OK")
        return True
    except Exception as e:
        print(f"WiFi reset fail: {e}")
        return False

def connect_wifi(ssid, password, state_machine, max_retries=10):
    global wlan
    
    state_machine.set_wifi_status("connecting")
    
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
    
    try:
        wlan.active(True)
        time.sleep(0.1)
        
        if wlan.isconnected():
            print(f"WiFi OK: {wlan.ifconfig()[0]}")
            state_machine.set_wifi_status("connected")
            return True
        
        print(f"WiFi→{ssid[:8]}...")
        try:
            wlan.connect(ssid, password)
        except Exception as e:
            print(f"WiFi err: {e}")
            if reset_wifi_interface():
                try:
                    wlan.connect(ssid, password)
                except:
                    state_machine.set_wifi_status("failed")
                    return False
            else:
                state_machine.set_wifi_status("failed")
                return False
        
        retry_count = 0
        blink_toggle = False
        last_blink_time = time.ticks_ms()
        
        while not wlan.isconnected() and retry_count < max_retries:
            current_time = time.ticks_ms()
            
            if time.ticks_diff(current_time, last_blink_time) >= NEOPIXEL_BLINK_INTERVAL:
                blink_toggle = not blink_toggle
                if neopixel_ctrl.is_enabled():
                    neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status(), blink_toggle)
                last_blink_time = current_time
                retry_count += 1
                if retry_count % 5 == 0:
                    print(f"[{retry_count}]", end="")
            
            time.sleep(0.05)
        
        if wlan.isconnected():
            print(f"\n✓WiFi: {wlan.ifconfig()[0]}")
            state_machine.set_wifi_status("connected")
            return True
        else:
            print("\n✗WiFi fail")
            state_machine.set_wifi_status("failed")
            return False
            
    except Exception as e:
        print(f"WiFi ex: {e}")
        state_machine.set_wifi_status("failed")
        return False

def reconnect_wifi(state_machine):
    """Robust WiFi reconnection with interface reset if needed"""
    global wlan
    
    print("WiFi recon...")
    
    if connect_wifi(WIFI_SSID, WIFI_PASSWORD, state_machine, max_retries=3):
        return True
    
    print("Reset WiFi iface...")
    if reset_wifi_interface():
        if connect_wifi(WIFI_SSID, WIFI_PASSWORD, state_machine, max_retries=WIFI_RECONNECT_MAX_RETRIES):
            return True
    
    print("WiFi recon fail")
    return False

def handle_locomotive_selection(state_machine, rocrail_protocol):
    """Handle locomotive selection button presses"""
    selection_changed = False
    
    # Handle UP button (next locomotive)
    if btn_up.is_pressed():
        if loco_list.select_next():
            selection_changed = True
    
    # Handle DOWN button (previous locomotive)
    if btn_down.is_pressed():
        if loco_list.select_previous():
            selection_changed = True
    
    # Update display if selection changed
    if selection_changed:
        update_locomotive_display()
        # Update direction indicator LEDs for new locomotive
        if neopixel_ctrl.is_enabled():
            neopixel_ctrl.direction_indicator_leds(loco_dir == "true")
        # Reset speed sending to ensure new locomotive starts safely
        state_machine.handle_locomotive_change()
        rocrail_protocol.send_speed_and_direction(0, loco_dir)
        print(f"Loco: {loco_list.get_selected_id()}")

def initialize_locomotive_list(rocrail_protocol):
    """Initialize locomotive list - load from file and query from RocRail for updates"""
    
    if loco_list.get_count() == 0:
        print("No locos→add default+query RR...")
        loco_list.add_locomotive(DEFAULT_LOCO_ID)
        loco_list.save_to_file()
    else:
        print(f"Loaded {loco_list.get_count()} locos")
    
    print("Query RR locos...")
    rocrail_protocol.query_locomotives()
    update_locomotive_display()

# Main program
run = True
if run:    
    # Connect to WiFi with robust reconnection
    if connect_wifi(WIFI_SSID, WIFI_PASSWORD, state_machine):
        
        # initialize the timer for regular events
        timer = IntervalTimer()
        
        # Connect to the rocrail server and start background monitoring
        print(f"RR→{ROCRAIL_HOST}:{ROCRAIL_PORT}")
        if rocrail_protocol.start_connection(ROCRAIL_HOST, ROCRAIL_PORT, rocrail_protocol.handle_data):
            
            # Initialize locomotive list
            initialize_locomotive_list(rocrail_protocol)
            
            # Initialize direction indicator LEDs
            if neopixel_ctrl.is_enabled():
                neopixel_ctrl.direction_indicator_leds(loco_dir == "true")
                print("[INIT] LEDs ready")
            
            # STARTUP STABILIZATION with NeoPixel refresh
            print("Startup stabilization...")
            for i in range(10):  # 3 seconds with NeoPixel refresh every 100ms
                time.sleep(0.1)
                if i % 10 == 0 and neopixel_ctrl.is_enabled():
                    neopixel_ctrl.refresh()  # Prevent early lockup
            print("System ready!")
            
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
                    
                    # NeoPixel stability refresh (prevent lockups)
                    if timer.is_ready("neopixel_refresh", 150):  # Every 2 seconds
                        if neopixel_ctrl.is_enabled():
                            neopixel_ctrl.refresh()
                    
                    # Memory monitoring every 60 seconds
                    if timer.is_ready("memory_check", 60000):
                        try:
                            import gc
                            gc.collect()
                            free_mem = gc.mem_free()
                            if free_mem < 15000:
                                print(f"[MEM] ⚠️ {free_mem}B")
                                gc.collect()
                                gc.collect()
                        except:
                            pass
                    
                    if timer.is_ready("check_wifi_update", WIFI_CHECK_INTERVAL):
                        try:
                            if not wlan or not wlan.isconnected():
                                print("WiFi lost→recon")
                                if state_machine.get_wifi_status() != "connecting":
                                    state_machine.set_wifi_status("connecting")
                                if reconnect_wifi(state_machine):
                                    print("WiFi✓")
                                else:
                                    state_machine.set_wifi_status("failed")
                            else:
                                if state_machine.get_wifi_status() != "connected":
                                    state_machine.set_wifi_status("connected")
                        except Exception as e:
                            print(f"WiFi ex: {e}")
                            state_machine.set_wifi_status("failed")
                            reset_wifi_interface()
                    
                    # Update status LEDs with blinking effects
                    if timer.is_ready("neopixel_blink", NEOPIXEL_BLINK_INTERVAL):
                        wifi_blink_toggle = not wifi_blink_toggle
                        rocrail_blink_toggle = not rocrail_blink_toggle
                        
                        if neopixel_ctrl.is_enabled():
                            neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status(), wifi_blink_toggle)
                            neopixel_ctrl.rocrail_status_led(rocrail_protocol.get_status(), rocrail_blink_toggle)
                            neopixel_ctrl.poti_zero_request_led(not state_machine.is_speed_sending_enabled(), wifi_blink_toggle)

                    # Handle locomotive selection buttons
                    if timer.is_ready("check_loco_selection", BUTTON_CHECK_INTERVAL):
                        handle_locomotive_selection(state_machine, rocrail_protocol)
                    
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
                            
                            # check direction button
                            if direction_button.is_pressed():
                                loco_dir = "true" if loco_dir == "false" else "false"
                                rocrail_protocol.send_speed_and_direction(0, loco_dir)
                                state_machine.handle_direction_change()
                                if neopixel_ctrl.is_enabled():
                                    neopixel_ctrl.direction_indicator_leds(loco_dir == "true")
                                print(f"D:{loco_dir[0]}")
                                
                            # check emergency button
                            if emergency_button.is_pressed():
                                rocrail_protocol.send_speed_and_direction(0, loco_dir)
                                state_machine.handle_emergency_stop()
                                print("⚠STOP!")
                            
                            # Light button pressed
                            if light_button.is_pressed():
                                loco_light = "true" if loco_light == "false" else "false"
                                rocrail_protocol.send_light_command(loco_light)
                                print(f"L:{loco_light[0]}")
                                
                            # Sound button pressed
                            if sound_button.is_pressed():
                                print("🔊Horn")
                                
                        except Exception as e:
                            print(f"[ERROR] Exception in poti/button handling: {e}")
                            import sys
                            sys.print_exception(e)
                
                    if timer.is_ready("update_speed", SPEED_UPDATE_INTERVAL):
                        try:
                            if state_machine.is_speed_sending_enabled():
                                if (speed != last_speed):
                                    print(f"V:{speed}")
                                    rocrail_protocol.send_speed_and_direction(speed, loco_dir)
                                    last_speed = speed
                            else:
                                state_machine.check_speed_enable_condition(speed)
                                if state_machine.is_speed_sending_enabled():
                                    print("V:enabled (poti=0)")
                        except Exception as e:
                            print(f"[ERR] Speed ex: {e}")
                            import sys
                            sys.print_exception(e)                       
                    
                    # Periodic cleanup after locomotives are loaded (every 5 minutes)
                    if rocrail_protocol.are_locomotives_loaded() and timer.is_ready("periodic_cleanup", 300000):
                        try:
                            import gc
                            print("[GC]...")
                            gc.collect()
                            gc.collect()
                            free_mem = gc.mem_free()
                            print(f"[GC] {free_mem}B free")
                        except Exception as e:
                            print(f"[GC] err: {e}")
                    
                    # Heartbeat every 30 seconds
                    if timer.is_ready("heartbeat", 30000):
                        print(f"[♥] W:{state_machine.get_wifi_status()[0]} R:{rocrail_protocol.get_status()[0]} V:{speed}")
                    
                    # Small delay to prevent CPU hogging
                    time.sleep(0.05)
                    
            except KeyboardInterrupt:
                print("Program interrupted")
                rocrail_protocol.stop_connection()
    else:
        print("WiFi connection failed")
        # WiFi status is already set to "failed" by connect_wifi function
        # Clear locomotive display
        if neopixel_ctrl.is_enabled():
            neopixel_ctrl.clear_locomotive_display()
        
        # Keep trying to reconnect and blink red LED
        timer = IntervalTimer()
        wifi_blink_toggle = False
        
        try:
            while True:
                # Update WiFi status LED (blinking red)
                if timer.is_ready("neopixel_blink", NEOPIXEL_BLINK_INTERVAL):
                    wifi_blink_toggle = not wifi_blink_toggle
                    if neopixel_ctrl.is_enabled():
                        neopixel_ctrl.wifi_status_led(state_machine.get_wifi_status(), wifi_blink_toggle)
                
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
            
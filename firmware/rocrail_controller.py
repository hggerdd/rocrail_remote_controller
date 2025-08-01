import network
import time
import socket
import select
import _thread
import machine
from machine import Pin

from rocrail_config import *
from lib.interval_timer import IntervalTimer
from lib.poti_controller import PotiController
from lib.button_controller import ButtonController
from lib.neopixel_controller import NeoPixelController
from lib.loco_list import LocoList

from btn_config import BTN_NOTHALT, BTN_RICHTUNGSWECHEL, BTN_GELB, BTN_BLAU, BTN_MITTE_UP, BTN_MITTE_DOWN
from btn_config import ADC_GESCHWINDIGKEIT

# Global variables for socket communication
socket_client = None
data_callback = None
running = False
wlan = None

sending_speed_enabled = True

# Initialize locomotive management
loco_list = LocoList(LOCO_LIST_FILE)
loco_dir = "true"
loco_light = "false"

# set the speed poti to get the desired speed
speed_poti = PotiController(pin_num=ADC_GESCHWINDIGKEIT, filter_size=5, threshold=1)
light_button = ButtonController(pin_num=BTN_BLAU, debounce_ms=5)
emergency_button = ButtonController(pin_num=BTN_NOTHALT, debounce_ms=5)
direction_button = ButtonController(pin_num=BTN_RICHTUNGSWECHEL, debounce_ms=5)
sound_button = ButtonController(pin_num=BTN_GELB, debounce_ms=5)

# Locomotive selection buttons
btn_up = ButtonController(pin_num=BTN_MITTE_UP, debounce_ms=5)
btn_down = ButtonController(pin_num=BTN_MITTE_DOWN, debounce_ms=5)

# Initialize NeoPixel controller - turns off all LEDs at startup
neopixel_ctrl = NeoPixelController(pin_num=NEOPIXEL_PIN, num_leds=NEOPIXEL_COUNT)

def connect_wifi(ssid, password, max_retries=10):
    global wlan
    
    # Create WLAN interface
    wlan = network.WLAN(network.STA_IF)
    
    # Activate the interface
    wlan.active(True)
    
    # Check if already connected
    if wlan.isconnected():
        print("Already connected to WiFi")
        print("Network config:", wlan.ifconfig())
        return True
    
    # Connect to WiFi
    print(f"Connecting to {ssid}...")
    wlan.connect(ssid, password)
    
    # Wait for connection with timeout
    retry_count = 0
    while not wlan.isconnected() and retry_count < max_retries:
        print("Waiting for connection...")
        time.sleep(1)
        retry_count += 1
    
    # Check connection status
    if wlan.isconnected():
        print("Connected to WiFi")
        print("Network config:", wlan.ifconfig())
        return True
    else:
        print("Failed to connect")
        return False

def socket_listener():
    global socket_client, data_callback, running
    
    poller = select.poll()
    poller.register(socket_client, select.POLLIN)
    
    buffer_size = 4096
    
    print("Socket listener started")
    
    while running:
        if poller.poll(100):  # Poll with 100ms timeout
            try:
                data = socket_client.recv(buffer_size)
                if data:
                    # Process data in the callback function
                    if data_callback:
                        data_callback(data)
                else:
                    # Connection closed by the server
                    print("Connection closed by server")
                    break
            except Exception as e:
                print(f"Socket error: {e}")
                break
    
    print("Socket listener stopped")

def start_socket_connection(host, port, callback_function):
    """
    Start a socket connection and monitor it in background
    
    Args:
        host: Server hostname or IP
        port: Server port
        callback_function: Function to call when data is received
    """
    global socket_client, data_callback, running
    
    try:
        # Create socket
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_client.connect((host, port))
        socket_client.setblocking(False)  # Non-blocking mode
        
        # Set callback function
        data_callback = callback_function
        running = True
        
        # Start listener thread
        _thread.start_new_thread(socket_listener, ())
        
        print(f"Connected to server {host}:{port}")
        return True
        
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def stop_socket_connection():
    """Stop the socket connection and background thread"""
    global socket_client, running
    
    if socket_client:
        running = False
        time.sleep(0.2)  # Give time for the thread to exit
        socket_client.close()
        socket_client = None
        print("Socket connection closed")

def handle_data(data):
    """Callback function for processing received data"""
    data_str = data.decode('utf-8', errors='ignore')
    print(f"Received data: {data_str}")
    
    # Check for locomotive list in response
    if '<lc ' in data_str and loco_list.get_count() == 0:
        # Try to update locomotive list from response
        if loco_list.update_from_rocrail_response(data_str):
            update_locomotive_display()

def send_poti_value(speed, direction):
    """Send potentiometer value through the socket connection in Rocrail RCP XML format to set the speed of the selected locomotive"""
    global socket_client
    
    current_loco_id = loco_list.get_selected_id()
    if not current_loco_id:
        print("No locomotive selected")
        return False
    
    if socket_client:
        try:
            # Format the message according to your protocol
            message = f'<lc id="{current_loco_id}" V="{speed}" dir="{direction}"/>'
            message_len = len(message)
            message_and_header = f'<xmlh><xml size="{message_len}"/></xmlh>{message}'
            socket_client.send(message_and_header.encode())
            
            print(message_and_header)
            
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    return False

def send_light_status(light_on_off):
    global socket_client
    
    current_loco_id = loco_list.get_selected_id()
    if not current_loco_id:
        print("No locomotive selected")
        return False
    
    if socket_client:
        try:
            message = f'<fn id="{current_loco_id}" fn0="{light_on_off}"/>'
            message_len = len(message)
            message_and_header = f'<xmlh><xml size="{message_len}"/></xmlh>{message}'
            socket_client.send(message_and_header.encode())
            
            print(message_and_header)
            
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    return False

def query_locomotives():
    """Query all locomotives from RocRail server"""
    global socket_client
    
    if socket_client:
        try:
            # Send query command to get all locomotives
            message = '<query/>'
            message_len = len(message)
            message_and_header = f'<xmlh><xml size="{message_len}"/></xmlh>{message}'
            socket_client.send(message_and_header.encode())
            
            print("Querying locomotives from RocRail...")
            print(message_and_header)
            
            return True
        except Exception as e:
            print(f"Query error: {e}")
            return False
    return False

def update_locomotive_display():
    """Update NeoPixel display to show current locomotive selection"""
    selected_index = loco_list.get_selected_index()
    total_locos = loco_list.get_count()
    neopixel_ctrl.update_locomotive_display(selected_index, total_locos)
    print(loco_list.get_status_string())

def handle_locomotive_selection():
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
        # Reset speed sending to ensure new locomotive starts safely
        global sending_speed_enabled
        sending_speed_enabled = False
        send_poti_value(0, loco_dir)

def initialize_locomotive_list():
    """Initialize locomotive list - load from file or query from RocRail"""
    if loco_list.get_count() == 0:
        # No locomotives loaded, add default and query for more
        print("No locomotives found, adding default and querying RocRail...")
        loco_list.add_locomotive(DEFAULT_LOCO_ID)
        loco_list.save_to_file()
        
        # Query RocRail for more locomotives
        query_locomotives()
    else:
        print(f"Loaded {loco_list.get_count()} locomotives from file")
    
    # Update display
    update_locomotive_display()

# Main program
run = True
if run:    
    # Connect to WiFi
    if connect_wifi(WIFI_SSID, WIFI_PASSWORD):
        print("WiFi connection successful")
        
        # Set initial WiFi status on LED 0 (green blinking)
        neopixel_ctrl.wifi_status_led(True, True)
        
        # initialize the timer for regular events
        timer = IntervalTimer()
        
        # Connect to the rocrail server and start background monitoring
        print("connect to " + ROCRAIL_HOST)
        if start_socket_connection(ROCRAIL_HOST, ROCRAIL_PORT, handle_data):
            
            # Initialize locomotive list
            initialize_locomotive_list()
            
            # Initialise speed values
            last_speed = -1
            speed = 0
            
            # Initialize WiFi status blinking
            wifi_blink_toggle = False
            
            try:
                # Main program loop
                while True:
                    
                    if timer.is_ready("check_wifi_update", WIFI_CHECK_INTERVAL):
                        print("check wifi connection")
                        if not wlan.isconnected():
                            print("!!! wifi not connected --> reconnect")
                    
                    # Update WiFi status LED (blinking)
                    if timer.is_ready("neopixel_blink", NEOPIXEL_BLINK_INTERVAL):
                        wifi_blink_toggle = not wifi_blink_toggle
                        neopixel_ctrl.wifi_status_led(wlan.isconnected(), wifi_blink_toggle)
                    
                    # Handle locomotive selection buttons
                    if timer.is_ready("check_loco_selection", BUTTON_CHECK_INTERVAL):
                        handle_locomotive_selection()
                    
                    # Query locomotives periodically if we have very few
                    if timer.is_ready("query_locomotives", LOCO_QUERY_INTERVAL):
                        if loco_list.get_count() <= 1:
                            query_locomotives()
                    
                    # regularly update the poti/button input controller (required to have enough values for mean)
                    if timer.is_ready("send_poti_update", POTI_UPDATE_INTERVAL):
                        
                        # update speed from poti position/angle
                        speed = speed_poti.read()
                        
                        # check direction button(incl. debouncing),
                        # toggle direction and set speed to 0,
                        # disable speed sending until the
                        # selection (poti) is set to speed 0
                        if direction_button.is_pressed():
                            loco_dir = "true" if loco_dir == "false" else "false"
                            send_poti_value(0, loco_dir)
                            sending_speed_enabled = False
                            print(f"Direction button pressed, toggle direction --> {loco_dir} set speed to zero to start again")
                            
                        # check emergency button
                        if emergency_button.is_pressed():
                            send_poti_value(0, loco_dir)
                            sending_speed_enabled = False
                            print("EMERGENCY STOP initiated, set speed to 0 to continue!!")
                        
                        # Light button pressed, toggle the light
                        if light_button.is_pressed():
                            loco_light = "true" if loco_light == "false" else "false"
                            send_light_status(loco_light)
                            print(f"Light button pressed, toggle light is {loco_light}")
                            
                        # Sound button pressed
                        if sound_button.is_pressed():
                            print(f"Sound button pressed, horn on for a short time")
                
                    # every SPEED_UPDATE_INTERVAL check if speed has changed and can be updated (avoid too many commands)
                    if timer.is_ready("update_speed", SPEED_UPDATE_INTERVAL):
                        if sending_speed_enabled:
                            if (speed != last_speed):
                                print(f"\nSpeed-Poti value: {speed}, {sending_speed_enabled} ---> ")
                                send_poti_value(speed, loco_dir)
                                last_speed = speed
                        else:
                            if speed == 0:
                                print("REENABLE SENDING")
                                sending_speed_enabled = True                       
                    
                    # Small delay to prevent CPU hogging
                    time.sleep(0.05)
                    
            except KeyboardInterrupt:
                print("Program interrupted")
                stop_socket_connection()
    else:
        print("WiFi connection failed")
        # Show WiFi connection failed on LED 0 (red blinking)
        neopixel_ctrl.wifi_status_led(False, True)
        # Clear locomotive display
        neopixel_ctrl.clear_locomotive_display()

# This file is executed on every boot (including wake-boot from deepsleep)
# depending on the pressed button the respective functionality is called

# red emergence stop button pushed at startup:
#     - Start the web configuration web server
#     - create an access point (AP)
#     - serve a fronend in html, css and java script
#     - the esp server offers the current visible networks and the user can
#       select one, set the passwort and send it to the esp who saves the password
#     - also the rocrail parameter (ip and port) can be set in the frontend and can
#       be saved in the esp
#
#  No button is pressed at startup:
#     - the standard mode is the rocrail controller
#     - we use the saved configuration for the wifi and for rocrail to connect
#     - and work with it
#
# green button is pressed at startup, we have a test program
#     - witht the black buttons we can set the numbers
#     - the poti sets the overall brightness of the leds
#     - with the yellow button we can select between the left and right side
#     - with the blue button we can make the 5th led blink


from machine import Pin
import sys
import time
from hardware_config import BTN_NOTHALT, BTN_RICHTUNGSWECHEL, NEOPIXEL_PIN, NEOPIXEL_COUNT
from lib.neopixel_controller import NeoPixelController
from hardware_config import LED_ROCRAIL

# turn off all neopixels at startup
np_ctrl = NeoPixelController(NEOPIXEL_PIN, NEOPIXEL_COUNT)
np_ctrl.all_off()
np_ctrl.refresh()

# Set LED_ROCRAIL to orange (preliminary state)
np_ctrl.set_led(LED_ROCRAIL, 255, 165, 0)  # Orange
np_ctrl.refresh()

# Configure your button pin (adjust pin number for your board)
red_button   = Pin(BTN_NOTHALT, Pin.IN, Pin.PULL_UP)
green_button = Pin(BTN_RICHTUNGSWECHEL, Pin.IN, Pin.PULL_UP)

# Small delay to allow button state to stabilize
time.sleep_ms(150)

# Check if button is pressed (LOW when using pull-up)
if not red_button.value():
    # Set LED_ROCRAIL to purple
    np_ctrl.set_led(LED_ROCRAIL, 128, 0, 128)  # Purple
    np_ctrl.refresh()

    print("\n\nRED Button pressed - Starting WiFi and rocrail configuration server...")
    time.sleep_ms(100)  # Debounce delay
    
    try:
        import wifi_config_server
        wifi_config_server.start_config_server()
    except ImportError:
        print("Error: wifi_config_server.py not found!")
    except Exception as e:
        print(f"Error running config server: {e}")
        
elif not green_button.value():  # Green button pressed at startup
    print("\n\nGreen Button pressed - REPL open, no program started")
    # Do nothing else, drop to REPL

else:
    # Set LED_ROCRAIL to green
    np_ctrl.set_led(LED_ROCRAIL, 0, 255, 0)  # Green
    np_ctrl.refresh()
    
    print("\n\nNormal startup - Running main program...")
    try:
        import rocrail_controller
    except ImportError:
        print("Error: rocrail_controller.py not found!")
    
    except Exception as e:
        print(f"Error running main rocrail_controller.py: {e}")



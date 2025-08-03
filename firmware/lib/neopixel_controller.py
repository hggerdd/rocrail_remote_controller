from machine import Pin
from neopixel import NeoPixel
import time
from rocrail_config import LED_WIFI, LED_ROCRAIL, LED_DIR_LEFT, LED_DIR_RIGHT, LED_ACTIVITY, LED_LOCO_START, LED_LOCO_END

class NeoPixelController:
    """Controller for 10 NeoPixel LEDs with status visualization"""
    
    def __init__(self, pin_num, num_leds=10):
        self.pin = Pin(pin_num, Pin.OUT)
        self.np = NeoPixel(self.pin, num_leds)
        self.num_leds = num_leds
        self.blink_state = {}
        
        # Turn off all LEDs immediately at startup
        self.all_off()
        
    def all_off(self):
        """Turn off all LEDs"""
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self.np.write()
        
    def set_led(self, led_num, r, g, b):
        """Set individual LED color"""
        if 0 <= led_num < self.num_leds:
            self.np[led_num] = (r, g, b)
            self.np.write()
    
    def wifi_status_led(self, status, blink_toggle=False):
        """Control WiFi status LED (LED 0)
        Args:
            status: 'initial', 'connecting', 'connected', 'failed'
            blink_toggle: True/False for blinking effect when needed
        """
        if status == 'initial':
            # Constant light orange at startup
            self.np[LED_WIFI] = (255, 165, 0)  # Orange
        elif status == 'connecting':
            # Blinking orange while trying to connect
            if blink_toggle:
                self.np[LED_WIFI] = (255, 165, 0)  # Orange on
            else:
                self.np[LED_WIFI] = (0, 0, 0)      # Off
        elif status == 'connected':
            # Green blinking when connected (save battery)
            if blink_toggle:
                self.np[LED_WIFI] = (0, 255, 0)    # Green on
            else:
                self.np[LED_WIFI] = (0, 0, 0)      # Off
        elif status == 'failed':
            # Red blinking when connection failed
            if blink_toggle:
                self.np[LED_WIFI] = (255, 0, 0)    # Red on
            else:
                self.np[LED_WIFI] = (0, 0, 0)      # Off
        else:
            # Unknown status - turn off
            self.np[LED_WIFI] = (0, 0, 0)
        self.np.write()
    
    def rocrail_status_led(self, status, blink_toggle=False):
        """Control RocRail connection status LED (LED 1)
        Args:
            status: 'disconnected', 'connecting', 'connected', 'lost'
            blink_toggle: True/False for blinking effect when needed
        """
        if status == 'disconnected':
            # Orange (initially)
            self.np[LED_ROCRAIL] = (255, 165, 0)
        elif status == 'connecting':
            # Blinking orange while trying to connect
            if blink_toggle:
                self.np[LED_ROCRAIL] = (255, 165, 0)  # Orange
            else:
                self.np[LED_ROCRAIL] = (0, 0, 0)      # Off
        elif status == 'connected':
            # Green when connected and receiving data
            self.np[LED_ROCRAIL] = (0, 255, 0)
        elif status == 'lost':
            # Red when connection lost
            self.np[LED_ROCRAIL] = (255, 0, 0)
        else:
            # Unknown status - turn off
            self.np[LED_ROCRAIL] = (0, 0, 0)
        
        self.np.write()
    
    def direction_indicator_leds(self, direction_value):
        """Control direction indicator LEDs (LEDs 2-3)
        Args:
            direction_value: True (forward, "<" yellow) or False (reverse, ">" yellow)
        """
        if direction_value:  # Direction "true" - forward
            self.np[LED_DIR_LEFT] = (255, 255, 0)   # "<" LED yellow
            self.np[LED_DIR_RIGHT] = (0, 0, 0)      # ">" LED off
        else:  # Direction "false" - reverse
            self.np[LED_DIR_LEFT] = (0, 0, 0)       # "<" LED off
            self.np[LED_DIR_RIGHT] = (255, 255, 0)  # ">" LED yellow
        
        self.np.write()
    
    def poti_zero_request_led(self, poti_zero_required, blink_toggle=False):
        """Control poti zero request LED (LED 4) - 5th LED
        Args:
            poti_zero_required: True if user must set poti to zero, False if normal operation
            blink_toggle: True/False for blinking effect when poti zero is required
        """
        if poti_zero_required:
            # Blink purple when user needs to set poti to zero
            if blink_toggle:
                self.np[LED_ACTIVITY] = (255, 0, 255)  # Purple
            else:
                self.np[LED_ACTIVITY] = (0, 0, 0)      # Off
        else:
            # Turn off LED when in normal operation (poti zero not required)
            self.np[LED_ACTIVITY] = (0, 0, 0)
        
        self.np.write()
    
    def activity_indicator_led(self, active, blink_toggle=False):
        """Control activity indicator LED (LED 4) - DEPRECATED: Use poti_zero_request_led instead
        Args:
            active: True if active, False if inactive
            blink_toggle: True/False for blinking effect when inactive
        """
        # Redirect to new method for backward compatibility
        self.poti_zero_request_led(not active, blink_toggle)
        
    def set_status_led(self, led_num, color, brightness=255):
        """Set status LED with brightness control
        Args:
            led_num: LED index (0-9)
            color: tuple (r, g, b) or string ('red', 'green', 'blue', 'yellow', 'off')
            brightness: 0-255
        """
        if led_num >= self.num_leds:
            return
            
        if isinstance(color, str):
            colors = {
                'red': (brightness, 0, 0),
                'green': (0, brightness, 0),
                'blue': (0, 0, brightness),
                'yellow': (brightness, brightness, 0),
                'cyan': (0, brightness, brightness),
                'magenta': (brightness, 0, brightness),
                'white': (brightness, brightness, brightness),
                'off': (0, 0, 0)
            }
            color = colors.get(color, (0, 0, 0))
        
        self.np[led_num] = color
        self.np.write()
    
    def update_locomotive_display(self, selected_index, total_locomotives):
        """Update LEDs 5-9 to show locomotive selection
        Args:
            selected_index: Index of currently selected locomotive (0-4)
            total_locomotives: Total number of available locomotives (0-5)
        """
        # LEDs 5-9 (indices 5-9) represent locomotives 1-5
        
        for i in range(LED_LOCO_START, LED_LOCO_END + 1):  # LEDs 5-9
            loco_index = i - LED_LOCO_START  # Convert to locomotive index (0-4)
            
            if loco_index < total_locomotives:
                if loco_index == selected_index:
                    # Selected locomotive: bright blue
                    self.np[i] = (0, 0, 255)
                else:
                    # Other locomotives: off (to save energy)
                    self.np[i] = (0, 0, 0)
            else:
                # No locomotive: off
                self.np[i] = (0, 0, 0)
        
        self.np.write()
    
    def clear_locomotive_display(self):
        """Turn off locomotive LEDs (5-9)"""
        for i in range(LED_LOCO_START, LED_LOCO_END + 1):
            self.np[i] = (0, 0, 0)
        self.np.write()
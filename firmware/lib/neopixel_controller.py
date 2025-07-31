from machine import Pin
from neopixel import NeoPixel
import time

class NeoPixelController:
    """Controller for 6 NeoPixel LEDs with status visualization"""
    
    def __init__(self, pin_num, num_leds=6):
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
    
    def wifi_status_led(self, is_connected, blink_toggle):
        """Control LED 1 (index 0) for WiFi status
        Args:
            is_connected: True if WiFi connected, False if disconnected
            blink_toggle: True/False for blinking effect
        """
        if is_connected:
            # Green blinking when connected (save battery)
            if blink_toggle:
                self.np[0] = (0, 255, 0)  # Green on
            else:
                self.np[0] = (0, 0, 0)    # Off
        else:
            # Red blinking when disconnected (80% brightness = 204)
            if blink_toggle:
                self.np[0] = (204, 0, 0)  # Red 80% brightness
            else:
                self.np[0] = (0, 0, 0)    # Off
        self.np.write()
        
    def set_status_led(self, led_num, color, brightness=255):
        """Set status LED with brightness control
        Args:
            led_num: LED index (0-5)
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

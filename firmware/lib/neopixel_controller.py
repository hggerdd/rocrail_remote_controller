from machine import Pin
from neopixel import NeoPixel
import time
from hardware_config import LED_WIFI, LED_ROCRAIL, LED_DIR_LEFT, LED_DIR_RIGHT, LED_ACTIVITY, LED_LOCO_START, LED_LOCO_END

class NeoPixelController:
    """Simple and reliable NeoPixel controller for 10 status LEDs"""
    
    def __init__(self, pin_num, num_leds=10):
        """Initialize NeoPixel with basic error handling"""
        self.pin_num = pin_num
        self.num_leds = num_leds
        self.enabled = True
        
        try:
            self.pin = Pin(self.pin_num, Pin.OUT)
            self.np = NeoPixel(self.pin, self.num_leds)
            self.all_off()
            print(f"[NEOPIXEL] Initialized on pin {self.pin_num}")
        except Exception as e:
            print(f"[NEOPIXEL] Init failed: {e}")
            self.enabled = False
    
    def _write(self):
        """Write to NeoPixel with minimal safety check"""
        if not self.enabled:
            return
        try:
            self.np.write()
        except:
            pass  # Silently ignore write errors
    
    def all_off(self):
        """Turn off all LEDs"""
        if not self.enabled:
            return
        for i in range(self.num_leds):
            self.np[i] = (0, 0, 0)
        self._write()
    
    def set_led(self, led_num, r, g, b):
        """Set individual LED color"""
        if not self.enabled or not (0 <= led_num < self.num_leds):
            return
        self.np[led_num] = (r, g, b)
        self._write()
    
    def wifi_status_led(self, status, blink=False):
        """WiFi status LED (0) - Green=connected, Orange=connecting, Red=failed"""
        if not self.enabled:
            return
            
        if status == 'connected':
            color = (0, 255, 0) if blink else (0, 50, 0)  # Green (bright/dim)
        elif status == 'connecting' or status == 'initial':
            color = (255, 165, 0) if blink else (0, 0, 0)  # Orange blink
        elif status == 'failed':
            color = (255, 0, 0) if blink else (0, 0, 0)  # Red blink
        else:
            color = (0, 0, 0)
        
        self.np[LED_WIFI] = color
        self._write()
    
    def rocrail_status_led(self, status, blink=False):
        """RocRail status LED (1) - Green=connected, Orange=connecting, Red=lost"""
        if not self.enabled:
            return
            
        if status == 'connected':
            color = (0, 255, 0)  # Solid green
        elif status == 'connecting' or status == 'disconnected':
            color = (255, 165, 0) if blink else (0, 0, 0)  # Orange blink
        elif status == 'reconnecting':
            color = (255, 100, 0) if blink else (0, 0, 0)  # Red-orange fast blink
        elif status == 'lost':
            color = (255, 0, 0)  # Solid red
        else:
            color = (0, 0, 0)
        
        self.np[LED_ROCRAIL] = color
        self._write()
    
    def direction_indicator_leds(self, forward):
        """Direction LEDs (2-3) - Yellow shows active direction"""
        if not self.enabled:
            return
            
        if forward:
            self.np[LED_DIR_LEFT] = (255, 255, 0)   # "<" yellow
            self.np[LED_DIR_RIGHT] = (0, 0, 0)      # ">" off
        else:
            self.np[LED_DIR_LEFT] = (0, 0, 0)       # "<" off
            self.np[LED_DIR_RIGHT] = (255, 255, 0)  # ">" yellow
        self._write()
    
    def poti_zero_request_led(self, required, blink=False):
        """Activity LED (4) - Purple blink when poti zero required"""
        if not self.enabled:
            return
            
        if required:
            color = (255, 0, 255) if blink else (0, 0, 0)  # Purple blink
        else:
            color = (0, 0, 0)  # Off when normal
        
        self.np[LED_ACTIVITY] = color
        self._write()
    
    def activity_indicator_led(self, active, blink=False):
        """Backward compatibility wrapper"""
        self.poti_zero_request_led(not active, blink)
    
    def update_locomotive_display(self, selected_idx, total_count):
        """Locomotive LEDs (5-9) - Blue for selected, off for others"""
        if not self.enabled:
            return
            
        for i in range(LED_LOCO_START, min(LED_LOCO_END + 1, LED_LOCO_START + total_count)):
            loco_idx = i - LED_LOCO_START
            if loco_idx == selected_idx:
                self.np[i] = (0, 0, 255)  # Blue for selected
            else:
                self.np[i] = (0, 0, 0)    # Off for others
        
        # Clear unused locomotive LEDs
        for i in range(LED_LOCO_START + total_count, LED_LOCO_END + 1):
            self.np[i] = (0, 0, 0)
        
        self._write()
    
    def clear_locomotive_display(self):
        """Turn off all locomotive LEDs"""
        if not self.enabled:
            return
        for i in range(LED_LOCO_START, LED_LOCO_END + 1):
            self.np[i] = (0, 0, 0)
        self._write()
    
    def is_enabled(self):
        """Check if LEDs are operational"""
        return self.enabled
    
    def force_disable(self):
        """Disable LED operations"""
        self.enabled = False
        print("[NEOPIXEL] Disabled")
    
    def try_recovery(self):
        """Simple recovery attempt"""
        if self.enabled:
            return True
        try:
            self.pin = Pin(self.pin_num, Pin.OUT)
            self.np = NeoPixel(self.pin, self.num_leds)
            self.enabled = True
            self.all_off()
            print("[NEOPIXEL] Recovery successful")
            return True
        except:
            return False

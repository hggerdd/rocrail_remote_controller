from machine import Pin
from neopixel import NeoPixel
import time
from hardware_config import LED_WIFI, LED_ROCRAIL, LED_DIR_LEFT, LED_DIR_RIGHT, LED_ACTIVITY, LED_LOCO_START, LED_LOCO_END

class NeoPixelController:
    """Controller for 10 NeoPixel LEDs with status visualization and RMT error recovery"""
    
    def __init__(self, pin_num, num_leds=10):
        self.pin_num = pin_num
        self.num_leds = num_leds
        self.led_enabled = True
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.last_error_time = 0
        
        # Initialize NeoPixel hardware
        self._init_neopixel()
        
        # Turn off all LEDs immediately at startup
        self.all_off()
        
    def _init_neopixel(self):
        """Initialize or re-initialize NeoPixel hardware"""
        try:
            self.pin = Pin(self.pin_num, Pin.OUT)
            self.np = NeoPixel(self.pin, self.num_leds)
            print(f"NeoPixel initialized successfully on pin {self.pin_num}")
            return True
        except Exception as e:
            print(f"[NEOPIXEL] Failed to initialize: {e}")
            self.led_enabled = False
            return False
    
    def _safe_write(self):
        """Safely write to NeoPixel with error recovery"""
        if not self.led_enabled:
            return False
            
        try:
            self.np.write()
            return True
        except Exception as e:
            current_time = time.ticks_ms()
            
            # Only attempt recovery if we haven't exceeded max attempts
            if self.recovery_attempts < self.max_recovery_attempts:
                # Limit recovery attempts to once per second
                if time.ticks_diff(current_time, self.last_error_time) > 1000:
                    print(f"[NEOPIXEL] Write error: {e}, attempting recovery ({self.recovery_attempts + 1}/{self.max_recovery_attempts})")
                    self.recovery_attempts += 1
                    self.last_error_time = current_time
                    
                    # Try to reinitialize NeoPixel
                    if self._init_neopixel():
                        print("[NEOPIXEL] Recovery successful")
                        try:
                            self.np.write()
                            return True
                        except:
                            pass
                    
            else:
                # Too many failed attempts - disable LEDs
                if self.led_enabled:
                    print(f"[NEOPIXEL] Disabling LEDs after {self.max_recovery_attempts} failed recovery attempts")
                    self.led_enabled = False
            
            return False
    
    def all_off(self):
        """Turn off all LEDs"""
        if not self.led_enabled:
            return
            
        try:
            for i in range(self.num_leds):
                self.np[i] = (0, 0, 0)
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in all_off: {e}")
            
    def set_led(self, led_num, r, g, b):
        """Set individual LED color"""
        if not self.led_enabled or not (0 <= led_num < self.num_leds):
            return
            
        try:
            self.np[led_num] = (r, g, b)
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error setting LED {led_num}: {e}")
    
    def wifi_status_led(self, status, blink_toggle=False):
        """Control WiFi status LED (LED 0) with error handling"""
        if not self.led_enabled:
            return
            
        try:
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
            
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in wifi_status_led: {e}")
    
    def rocrail_status_led(self, status, blink_toggle=False):
        """Control RocRail connection status LED (LED 1) with error handling"""
        if not self.led_enabled:
            return
            
        try:
            if status == 'disconnected':
                # Orange (initially)
                self.np[LED_ROCRAIL] = (255, 165, 0)
            elif status == 'connecting':
                # Blinking orange while trying to connect
                if blink_toggle:
                    self.np[LED_ROCRAIL] = (255, 165, 0)  # Orange
                else:
                    self.np[LED_ROCRAIL] = (0, 0, 0)      # Off
            elif status == 'reconnecting':
                # Fast blinking red while reconnecting
                if blink_toggle:
                    self.np[LED_ROCRAIL] = (255, 100, 0)  # Red-orange
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
            
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in rocrail_status_led: {e}")
    
    def direction_indicator_leds(self, direction_value):
        """Control direction indicator LEDs (LEDs 2-3) with error handling"""
        if not self.led_enabled:
            return
            
        try:
            if direction_value:  # Direction "true" - forward
                self.np[LED_DIR_LEFT] = (255, 255, 0)   # "<" LED yellow
                self.np[LED_DIR_RIGHT] = (0, 0, 0)      # ">" LED off
            else:  # Direction "false" - reverse
                self.np[LED_DIR_LEFT] = (0, 0, 0)       # "<" LED off
                self.np[LED_DIR_RIGHT] = (255, 255, 0)  # ">" LED yellow
            
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in direction_indicator_leds: {e}")
    
    def poti_zero_request_led(self, poti_zero_required, blink_toggle=False):
        """Control poti zero request LED (LED 4) with error handling"""
        if not self.led_enabled:
            return
            
        try:
            if poti_zero_required:
                # Blink purple when user needs to set poti to zero
                if blink_toggle:
                    self.np[LED_ACTIVITY] = (255, 0, 255)  # Purple
                else:
                    self.np[LED_ACTIVITY] = (0, 0, 0)      # Off
            else:
                # Turn off LED when in normal operation (poti zero not required)
                self.np[LED_ACTIVITY] = (0, 0, 0)
            
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in poti_zero_request_led: {e}")
    
    def activity_indicator_led(self, active, blink_toggle=False):
        """Control activity indicator LED (LED 4) - DEPRECATED: Use poti_zero_request_led instead"""
        # Redirect to new method for backward compatibility
        self.poti_zero_request_led(not active, blink_toggle)
        
    def set_status_led(self, led_num, color, brightness=255):
        """Set status LED with brightness control and error handling"""
        if not self.led_enabled or led_num >= self.num_leds:
            return
            
        try:
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
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in set_status_led: {e}")
    
    def update_locomotive_display(self, selected_index, total_locomotives):
        """Update LEDs 5-9 to show locomotive selection with error handling"""
        if not self.led_enabled:
            return
            
        try:
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
            
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in update_locomotive_display: {e}")
    
    def clear_locomotive_display(self):
        """Turn off locomotive LEDs (5-9) with error handling"""
        if not self.led_enabled:
            return
            
        try:
            for i in range(LED_LOCO_START, LED_LOCO_END + 1):
                self.np[i] = (0, 0, 0)
            self._safe_write()
        except Exception as e:
            print(f"[NEOPIXEL] Error in clear_locomotive_display: {e}")
    
    def is_enabled(self):
        """Check if NeoPixel LEDs are currently enabled"""
        return self.led_enabled
    
    def force_disable(self):
        """Permanently disable LED operations"""
        self.led_enabled = False
        print("[NEOPIXEL] LEDs manually disabled")
    
    def try_recovery(self):
        """Manual recovery attempt - reset error counters and try again"""
        print("[NEOPIXEL] Manual recovery attempt...")
        self.recovery_attempts = 0
        self.last_error_time = 0
        if self._init_neopixel():
            self.led_enabled = True
            print("[NEOPIXEL] Manual recovery successful")
            return True
        else:
            print("[NEOPIXEL] Manual recovery failed")
            return False
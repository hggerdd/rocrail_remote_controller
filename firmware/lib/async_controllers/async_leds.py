"""
Async NeoPixel LED Controller
Handles LED status updates with asyncio
"""

import asyncio
import time
from hardware_config import *

try:
    from neopixel import NeoPixel
    from machine import Pin
    NEOPIXEL_AVAILABLE = True
except ImportError:
    NEOPIXEL_AVAILABLE = False
    print("NeoPixel not available")


class AsyncNeoPixelController:
    """
    Async NeoPixel LED controller
    Handles status visualization with asyncio timing
    """
    
    def __init__(self):
        self.neo = None
        self.enabled = False
        
        # LED brightness levels
        self.LED_BRIGHT = 255
        self.LED_DIM_HIGH = 50
        self.LED_DIM_LOW = 20
        self.LED_OFF = 0
        
        # Blinking state
        self._blink_state = False
        self._last_blink_time = 0
        
        # Async synchronization
        self._led_lock = asyncio.Lock()
        
        # LED state cache to avoid unnecessary updates
        self._led_states = {}
        
    async def initialize(self):
        """Initialize NeoPixel LEDs"""
        if not NEOPIXEL_AVAILABLE:
            print("NeoPixel not available - LED updates disabled")
            return True
            
        try:
            self.neo = NeoPixel(Pin(NEOPIXEL_PIN), NEOPIXEL_COUNT)
            
            # Clear all LEDs
            await self._clear_all()
            
            self.enabled = True
            print("✓ Async NeoPixel initialized")
            return True
            
        except Exception as e:
            print(f"NeoPixel init error: {e}")
            self.enabled = False
            return False
            
    async def cleanup(self):
        """Cleanup LEDs"""
        if self.enabled:
            await self._clear_all()
            
    async def _clear_all(self):
        """Clear all LEDs"""
        async with self._led_lock:
            if self.neo:
                try:
                    for i in range(NEOPIXEL_COUNT):
                        self.neo[i] = (0, 0, 0)
                    self.neo.write()
                except:
                    pass  # Silent error handling
                    
    async def _set_led(self, index, color, force_update=False):
        """Set LED color with state caching"""
        if not self.enabled or not self.neo:
            return
            
        # Check if color actually changed
        if not force_update and self._led_states.get(index) == color:
            return
            
        async with self._led_lock:
            try:
                self.neo[index] = color
                self.neo.write()
                self._led_states[index] = color
            except:
                pass  # Silent error handling
                
    async def _update_blink_state(self):
        """Update global blink state"""
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self._last_blink_time) >= NEOPIXEL_BLINK_INTERVAL:
            self._blink_state = not self._blink_state
            self._last_blink_time = current_time
            
    async def update_wifi_status(self, status):
        """Update WiFi status LED"""
        await self._update_blink_state()
        
        if status == "connected":
            # Green with dim/bright pulsing
            brightness = self.LED_BRIGHT if self._blink_state else self.LED_DIM_HIGH
            color = (0, brightness, 0)
        elif status == "connecting":
            # Orange blinking
            brightness = self.LED_BRIGHT if self._blink_state else self.LED_DIM_LOW
            color = (brightness, brightness//2, 0)
        elif status == "failed":
            # Red blinking
            brightness = self.LED_BRIGHT if self._blink_state else self.LED_DIM_LOW
            color = (brightness, 0, 0)
        else:
            # Off for initial/unknown states
            color = (0, 0, 0)
            
        await self._set_led(LED_WIFI, color)
        
    async def update_rocrail_status(self, status):
        """Update RocRail status LED"""
        await self._update_blink_state()
        
        if status == "connected":
            # Solid green
            color = (0, self.LED_BRIGHT, 0)
        elif status == "connecting":
            # Orange blinking
            brightness = self.LED_BRIGHT if self._blink_state else self.LED_DIM_LOW
            color = (brightness, brightness//2, 0)
        elif status == "reconnecting":
            # Red-orange fast blinking
            brightness = self.LED_BRIGHT if self._blink_state else self.LED_DIM_LOW
            color = (brightness, brightness//3, 0)
        elif status == "lost":
            # Solid red
            color = (self.LED_BRIGHT, 0, 0)
        else:
            # Off for disconnected/unknown
            color = (0, 0, 0)
            
        await self._set_led(LED_ROCRAIL, color)
        
    async def update_direction(self, is_forward):
        """Update direction indicator LEDs"""
        if is_forward:
            # Left LED bright yellow (forward)
            await self._set_led(LED_DIR_LEFT, (self.LED_BRIGHT, self.LED_BRIGHT, 0))
            await self._set_led(LED_DIR_RIGHT, (0, 0, 0))
        else:
            # Right LED bright yellow (reverse)
            await self._set_led(LED_DIR_LEFT, (0, 0, 0))
            await self._set_led(LED_DIR_RIGHT, (self.LED_BRIGHT, self.LED_BRIGHT, 0))
            
    async def update_speed_warning(self, warning_active):
        """Update speed warning LED (poti zero required)"""
        if warning_active:
            await self._update_blink_state()
            # Purple blinking when poti zero required
            brightness = self.LED_BRIGHT if self._blink_state else self.LED_DIM_LOW
            color = (brightness//2, 0, brightness)
        else:
            # Off when normal operation
            color = (0, 0, 0)
            
        await self._set_led(LED_ACTIVITY, color)
        
    async def update_locomotive_selection(self, selected_index, total_locos):
        """Update locomotive selection LEDs"""
        # Clear all locomotive LEDs first
        for i in range(5):  # LEDs 5-9
            await self._set_led(LED_LOCO_START + i, (0, 0, 0))
            
        # Light up selected locomotive LED
        if selected_index >= 0 and selected_index < 5 and selected_index < total_locos:
            led_index = LED_LOCO_START + selected_index
            await self._set_led(led_index, (0, 0, self.LED_BRIGHT))  # Bright blue
            
    async def show_startup_sequence(self):
        """Show startup LED sequence"""
        if not self.enabled:
            return
            
        print("LED startup sequence...")
        
        # Flash WiFi LED orange (initializing)
        await self._set_led(LED_WIFI, (255, 165, 0), force_update=True)
        await asyncio.sleep(0.2)
        
        # Flash RocRail LED orange (initializing) 
        await self._set_led(LED_ROCRAIL, (255, 165, 0), force_update=True)
        await asyncio.sleep(0.2)
        
        # Quick sweep of locomotive LEDs to show system alive
        for i in range(5):
            led_index = LED_LOCO_START + i
            await self._set_led(led_index, (0, 0, 100), force_update=True)
            await asyncio.sleep(0.05)
            await self._set_led(led_index, (0, 0, 0), force_update=True)
            
        print("✓ LED startup complete - ready for status updates")
        
    async def show_error_pattern(self):
        """Show error pattern on LEDs"""
        if not self.enabled:
            return
            
        # Flash all LEDs red
        for _ in range(3):
            for i in range(NEOPIXEL_COUNT):
                await self._set_led(i, (self.LED_BRIGHT, 0, 0), force_update=True)
            await asyncio.sleep(0.2)
            await self._clear_all()
            await asyncio.sleep(0.2)
            
    async def test_all_leds(self):
        """Test all LEDs with different colors"""
        if not self.enabled:
            return
            
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green  
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 255, 255),# White
        ]
        
        for color in colors:
            for i in range(NEOPIXEL_COUNT):
                await self._set_led(i, color, force_update=True)
            await asyncio.sleep(0.5)
            
        await self._clear_all()
        
    async def refresh(self):
        """Refresh LEDs (prevent RMT lockups)"""
        if self.enabled and self.neo:
            async with self._led_lock:
                try:
                    self.neo.write()
                except:
                    pass  # Silent error handling
                    
    def is_enabled(self):
        """Check if LEDs are enabled"""
        return self.enabled
        
    def force_disable(self):
        """Force disable LEDs"""
        self.enabled = False
        print("NeoPixel force disabled")

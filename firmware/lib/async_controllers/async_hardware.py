"""
Async Hardware Management
Handles buttons, potentiometer with asyncio
"""

import asyncio
import time
from machine import Pin, ADC
from hardware_config import *


class AsyncHardwareManager:
    """
    Async hardware input manager
    Replaces polling with async button/potentiometer reading
    """
    
    def __init__(self):
        # Initialize hardware pins
        self.buttons = {}
        self.speed_adc = None
        
        # Button debouncing state - simplified
        self._last_button_states = {}
        self._last_button_times = {}
        
        # Speed filtering
        self._speed_samples = []
        self._speed_filter_size = 5
        self._speed_threshold = 1
        
        # Async synchronization
        self._hardware_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize hardware pins"""
        print("Initializing async hardware...")
        
        try:
            # Initialize buttons
            self.buttons = {
                'emergency': Pin(BTN_NOTHALT, Pin.IN, Pin.PULL_UP),
                'direction': Pin(BTN_RICHTUNGSWECHEL, Pin.IN, Pin.PULL_UP), 
                'sound': Pin(BTN_GELB, Pin.IN, Pin.PULL_UP),
                'light': Pin(BTN_BLAU, Pin.IN, Pin.PULL_UP),
                'btn_up': Pin(BTN_MITTE_UP, Pin.IN, Pin.PULL_UP),
                'btn_down': Pin(BTN_MITTE_DOWN, Pin.IN, Pin.PULL_UP)
            }
            
            # Initialize button states - simplified
            for name in self.buttons:
                self._last_button_states[name] = self.buttons[name].value()  # Store actual pin value
                self._last_button_times[name] = time.ticks_ms()
                
            # Initialize speed potentiometer
            self.speed_adc = ADC(Pin(ADC_GESCHWINDIGKEIT))
            self.speed_adc.atten(ADC.ATTN_11DB)
            
            # Initialize speed filter
            for _ in range(self._speed_filter_size):
                raw_value = self.speed_adc.read()
                speed = int((raw_value / 4095.0) * 126)
                self._speed_samples.append(speed)
                
            print("✓ Async hardware initialized")
            return True
            
        except Exception as e:
            print(f"Hardware initialization error: {e}")
            return False
            
    async def _read_button_debounced(self, name, debounce_ms=20):
        """Read button with simple debouncing - returns True on button press"""
        if name not in self.buttons:
            return False
            
        current_time = time.ticks_ms()
        current_value = self.buttons[name].value()  # 0 = pressed (pull-up), 1 = not pressed
        
        # Check if enough time has passed since last state change
        time_since_last = time.ticks_diff(current_time, self._last_button_times[name])
        if time_since_last < debounce_ms:
            return False
            
        # Check for button press (transition from 1 to 0 for pull-up)
        if self._last_button_states[name] == 1 and current_value == 0:
            # Button was just pressed
            self._last_button_states[name] = current_value
            self._last_button_times[name] = current_time
            print(f"[BUTTON] {name} press detected!")  # Debug output
            return True
            
        # Update state if it changed
        if self._last_button_states[name] != current_value:
            self._last_button_states[name] = current_value
            self._last_button_times[name] = current_time
            
        return False
        
    async def _read_speed_filtered(self):
        """Read speed potentiometer with filtering"""
        try:
            # Read raw ADC value
            raw_value = self.speed_adc.read()
            speed = int((raw_value / 4095.0) * 126)
            
            # Update sliding window filter
            self._speed_samples.append(speed)
            if len(self._speed_samples) > self._speed_filter_size:
                self._speed_samples.pop(0)
                
            # Calculate filtered average
            filtered_speed = sum(self._speed_samples) // len(self._speed_samples)
            
            return max(0, min(126, filtered_speed))
            
        except Exception as e:
            print(f"Speed read error: {e}")
            return 0
            
    async def read_all_inputs(self):
        """Read all hardware inputs asynchronously"""
        async with self._hardware_lock:
            try:
                # Read all buttons
                buttons = {}
                for name in self.buttons:
                    buttons[name] = await self._read_button_debounced(name)
                    
                # Read speed 
                speed = await self._read_speed_filtered()
                
                return {
                    'emergency': buttons['emergency'],
                    'direction': buttons['direction'],
                    'sound': buttons['sound'],
                    'light': buttons['light'],
                    'btn_up': buttons['btn_up'],
                    'btn_down': buttons['btn_down'],
                    'speed': speed
                }
                
            except Exception as e:
                print(f"Input reading error: {e}")
                return {
                    'emergency': False,
                    'direction': False, 
                    'sound': False,
                    'light': False,
                    'btn_up': False,
                    'btn_down': False,
                    'speed': 0
                }
                
    async def get_speed(self):
        """Get current filtered speed value"""
        async with self._hardware_lock:
            return await self._read_speed_filtered()

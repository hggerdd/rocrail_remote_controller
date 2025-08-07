"""
Async WiFi Manager
Replaces blocking WiFi operations with asyncio
"""

import asyncio
import network
import time


class AsyncWiFiManager:
    """
    Async WiFi management
    Handles connection, reconnection, and monitoring
    """
    
    def __init__(self, state_manager):
        self.state = state_manager
        self.wlan = None
        
        # Connection parameters
        self.ssid = None
        self.password = None
        self.max_retries = 10
        
        # Async synchronization
        self._wifi_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize WiFi interface"""
        async with self._wifi_lock:
            try:
                self.wlan = network.WLAN(network.STA_IF)
                self.wlan.active(True)
                await asyncio.sleep(0.5)
                return True
            except Exception as e:
                print(f"WiFi init error: {e}")
                return False
                
    async def connect(self, ssid, password, timeout_seconds=30):
        """Connect to WiFi with async timeout"""
        self.ssid = ssid
        self.password = password
        
        await self.state.set_wifi_status("connecting")
        
        if not self.wlan:
            await self.initialize()
            
        async with self._wifi_lock:
            try:
                # Check if already connected
                if self.wlan.isconnected():
                    print(f"WiFi already connected: {self.wlan.ifconfig()[0]}")
                    await self.state.set_wifi_status("connected")
                    return True
                    
                print(f"Connecting to WiFi: {ssid[:8]}...")
                
                # Start connection
                self.wlan.connect(ssid, password)
                
                # Wait for connection with timeout - MicroPython compatible
                start_time = time.ticks_ms()
                timeout_ms = timeout_seconds * 1000
                while not self.wlan.isconnected():
                    if time.ticks_diff(time.ticks_ms(), start_time) > timeout_ms:
                        print("WiFi connection timeout")
                        await self.state.set_wifi_status("failed")
                        return False
                        
                    await asyncio.sleep(0.1)
                    
                # Connection successful
                ip = self.wlan.ifconfig()[0]
                print(f"✓ WiFi connected: {ip}")
                await self.state.set_wifi_status("connected")
                return True
                
            except Exception as e:
                print(f"WiFi connection error: {e}")
                await self.state.set_wifi_status("failed")
                return False
                
    async def disconnect(self):
        """Disconnect from WiFi"""
        async with self._wifi_lock:
            try:
                if self.wlan and self.wlan.isconnected():
                    self.wlan.disconnect()
                    print("WiFi disconnected")
                    
                if self.wlan:
                    self.wlan.active(False)
                    
                await self.state.set_wifi_status("disconnected")
                
            except Exception as e:
                print(f"WiFi disconnect error: {e}")
                
    async def is_connected(self):
        """Check if WiFi is connected"""
        async with self._wifi_lock:
            try:
                return self.wlan and self.wlan.isconnected()
            except Exception as e:
                print(f"WiFi status check error: {e}")
                return False
                
    async def get_ip(self):
        """Get current IP address"""
        async with self._wifi_lock:
            try:
                if self.wlan and self.wlan.isconnected():
                    return self.wlan.ifconfig()[0]
                return None
            except Exception as e:
                print(f"IP get error: {e}")
                return None
                
    async def reset_interface(self):
        """Reset WiFi interface for error recovery"""
        async with self._wifi_lock:
            try:
                print("Resetting WiFi interface...")
                
                if self.wlan:
                    self.wlan.disconnect()
                    self.wlan.active(False)
                    await asyncio.sleep(1)
                    
                self.wlan = network.WLAN(network.STA_IF)
                self.wlan.active(True)
                await asyncio.sleep(0.5)
                
                print("WiFi interface reset complete")
                return True
                
            except Exception as e:
                print(f"WiFi interface reset error: {e}")
                return False
                
    async def reconnect(self, max_attempts=3):
        """Attempt to reconnect WiFi"""
        if not self.ssid or not self.password:
            print("No WiFi credentials for reconnection")
            return False
            
        print("Attempting WiFi reconnection...")
        
        # Try simple reconnection first
        if await self.connect(self.ssid, self.password, timeout_seconds=10):
            return True
            
        # Try with interface reset
        for attempt in range(max_attempts):
            print(f"WiFi reconnection attempt {attempt + 1}/{max_attempts}")
            
            if await self.reset_interface():
                if await self.connect(self.ssid, self.password, timeout_seconds=15):
                    return True
                    
            await asyncio.sleep(2)  # Wait between attempts
            
        print("WiFi reconnection failed")
        return False
        
    async def get_signal_strength(self):
        """Get WiFi signal strength (RSSI)"""
        async with self._wifi_lock:
            try:
                if self.wlan and self.wlan.isconnected():
                    return self.wlan.status('rssi')
                return None
            except Exception as e:
                print(f"Signal strength error: {e}")
                return None

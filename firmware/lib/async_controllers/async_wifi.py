"""
Async WiFi Manager
Replaces blocking WiFi operations with asyncio
"""

import asyncio
import network
import time
import ujson as json  # MicroPython compatible
import os


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
        self.known_networks = None  # Loaded from file
        
        # Async synchronization
        self._wifi_lock = asyncio.Lock()

    async def _load_known_networks(self, filename="wifi_networks.txt"):
        """Load known networks from JSON file"""
        try:
            if not self.known_networks:
                if filename in os.listdir():
                    with open(filename, "r") as f:
                        self.known_networks = json.load(f)
                else:
                    print("WiFi: No known networks file found.")
                    self.known_networks = []
            return self.known_networks
        except Exception as e:
            print(f"WiFi: Failed to load known networks: {e}")
            self.known_networks = []
            return []

    async def _select_best_network(self):
        """Scan and select the strongest known network"""
        try:
            await self._load_known_networks()
            if not self.known_networks:
                print("WiFi: No known networks to connect.")
                return None, None

            scan_results = self.wlan.scan()
            # scan_results: list of tuples (ssid, bssid, channel, RSSI, security, hidden)
            available = {}
            for net in scan_results:
                ssid = net[0].decode() if isinstance(net[0], bytes) else net[0]
                rssi = net[3]
                available[ssid] = rssi

            # Find matching SSIDs
            candidates = []
            for entry in self.known_networks:
                ssid = entry.get("ssid")
                if ssid in available:
                    candidates.append((ssid, entry.get("password"), available[ssid]))

            if not candidates:
                print("WiFi: No known networks found in scan.")
                return None, None

            # Select the one with highest RSSI
            best = max(candidates, key=lambda x: x[2])
            print(f"WiFi: Selected network '{best[0]}' with RSSI {best[2]}")
            return best[0], best[1]
        except Exception as e:
            print(f"WiFi: Error selecting best network: {e}")
            return None, None

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

    async def connect(self, timeout_seconds=30):
        """Connect to WiFi with async timeout. Selects strongest known network automatically."""
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

                # Select best network if not already chosen
                if not self.ssid or not self.password:
                    self.ssid, self.password = await self._select_best_network()
                    if not self.ssid or not self.password:
                        print("WiFi: No suitable network credentials found.")
                        await self.state.set_wifi_status("failed")
                        return False

                print(f"Connecting to WiFi: {self.ssid[:8]}...")

                # Start connection
                self.wlan.connect(self.ssid, self.password)

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
            # Try to select a network again
            self.ssid, self.password = await self._select_best_network()
            if not self.ssid or not self.password:
                print("No WiFi credentials for reconnection")
                return False

        print("Attempting WiFi reconnection...")

        # Try simple reconnection first
        if await self.connect(timeout_seconds=10):
            return True

        # Try with interface reset
        for attempt in range(max_attempts):
            print(f"WiFi reconnection attempt {attempt + 1}/{max_attempts}")

            if await self.reset_interface():
                if await self.connect(timeout_seconds=15):
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

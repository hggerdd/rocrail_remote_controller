"""
Async Controller State Management
Replaces global variables with asyncio-based state management
"""

import asyncio
import time


class AsyncControllerState:
    """
    Async state management using asyncio primitives
    Replaces global variables and manual state tracking
    """
    
    def __init__(self):
        # State variables with asyncio protection
        self._wifi_status = "initial"  # "initial", "connecting", "connected", "failed"
        self._rocrail_status = "disconnected"  # "disconnected", "connecting", "connected", "lost", "reconnecting"
        self._speed_enabled = True
        
        # Asyncio synchronization primitives
        self._state_lock = asyncio.Lock()
        self._wifi_changed = asyncio.Event()
        self._rocrail_changed = asyncio.Event()
        self._speed_changed = asyncio.Event()
        
        # Event signaling for state changes
        self._locomotive_changed = asyncio.Event()
        self._direction_changed = asyncio.Event()
        self._emergency_stop = asyncio.Event()
        
        # Status change tracking
        self._last_wifi_status = None
        self._last_rocrail_status = None
        self._last_speed_enabled = None
        
    async def get_wifi_status(self):
        """Get current WiFi status (thread-safe)"""
        async with self._state_lock:
            return self._wifi_status
            
    async def set_wifi_status(self, status):
        """Set WiFi status and signal change"""
        async with self._state_lock:
            if self._wifi_status != status:
                old_status = self._wifi_status
                self._wifi_status = status
                print(f"WiFi: {old_status} -> {status}")
                self._wifi_changed.set()
                
    async def wait_wifi_change(self):
        """Wait for WiFi status change"""
        await self._wifi_changed.wait()
        self._wifi_changed.clear()
        
    async def get_rocrail_status(self):
        """Get current RocRail status (thread-safe)"""
        async with self._state_lock:
            return self._rocrail_status
            
    async def set_rocrail_status(self, status):
        """Set RocRail status and signal change"""
        async with self._state_lock:
            if self._rocrail_status != status:
                old_status = self._rocrail_status
                self._rocrail_status = status
                print(f"RocRail: {old_status} -> {status}")
                self._rocrail_changed.set()
                
    async def wait_rocrail_change(self):
        """Wait for RocRail status change"""
        await self._rocrail_changed.wait()
        self._rocrail_changed.clear()
        
    async def is_speed_enabled(self):
        """Check if speed sending is enabled (thread-safe)"""
        async with self._state_lock:
            return self._speed_enabled
            
    async def enable_speed_sending(self):
        """Enable speed sending"""
        async with self._state_lock:
            if not self._speed_enabled:
                self._speed_enabled = True
                print("Speed sending enabled")
                self._speed_changed.set()
                
    async def disable_speed_sending(self):
        """Disable speed sending (safety mechanism)"""
        async with self._state_lock:
            if self._speed_enabled:
                self._speed_enabled = False
                print("Speed sending disabled - POTI ZERO REQUIRED")
                self._speed_changed.set()
                
    async def wait_speed_change(self):
        """Wait for speed enable state change"""
        await self._speed_changed.wait()
        self._speed_changed.clear()
        
    # Event signaling methods
    async def signal_locomotive_changed(self):
        """Signal locomotive selection changed"""
        await self.disable_speed_sending()
        self._locomotive_changed.set()
        
    async def wait_locomotive_changed(self):
        """Wait for locomotive change event"""
        await self._locomotive_changed.wait()
        self._locomotive_changed.clear()
        
    async def signal_direction_changed(self):
        """Signal direction changed"""
        await self.disable_speed_sending()
        self._direction_changed.set()
        
    async def wait_direction_changed(self):
        """Wait for direction change event"""
        await self._direction_changed.wait()
        self._direction_changed.clear()
        
    async def signal_emergency_stop(self):
        """Signal emergency stop"""
        await self.disable_speed_sending()
        self._emergency_stop.set()
        
    async def wait_emergency_stop(self):
        """Wait for emergency stop event"""
        await self._emergency_stop.wait()
        self._emergency_stop.clear()
        
    async def get_system_status(self):
        """Get comprehensive system status"""
        async with self._state_lock:
            return {
                'wifi_connected': self._wifi_status == "connected",
                'rocrail_connected': self._rocrail_status == "connected", 
                'speed_enabled': self._speed_enabled,
                'system_ready': (self._wifi_status == "connected" and 
                               self._rocrail_status == "connected" and 
                               self._speed_enabled)
            }
            
    async def has_status_changed(self):
        """Check if any status changed since last call"""
        async with self._state_lock:
            changed = (
                self._last_wifi_status != self._wifi_status or
                self._last_rocrail_status != self._rocrail_status or
                self._last_speed_enabled != self._speed_enabled
            )
            
            # Update last known states
            self._last_wifi_status = self._wifi_status
            self._last_rocrail_status = self._rocrail_status
            self._last_speed_enabled = self._speed_enabled
            
            return changed
            
    async def wait_system_ready(self):
        """Wait until system is ready (WiFi + RocRail connected)"""
        while True:
            status = await self.get_system_status()
            if status['wifi_connected'] and status['rocrail_connected']:
                return
            await asyncio.sleep(0.1)

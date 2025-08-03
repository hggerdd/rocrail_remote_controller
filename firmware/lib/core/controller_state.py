import time


class ControllerStateMachine:
    """
    Manages the overall state of the locomotive controller.
    Coordinates WiFi, RocRail connection, and locomotive control states.
    """
    
    def __init__(self):
        # WiFi connection status
        self.wifi_status = "initial"  # States: "initial", "connecting", "connected", "failed"
        
        # Speed control state
        self.sending_speed_enabled = True
        
        # Last known states for change detection
        self._last_wifi_status = None
        self._last_rocrail_status = None
        self._last_speed_enabled = None
    
    def get_wifi_status(self):
        """Get current WiFi status"""
        return self.wifi_status
    
    def set_wifi_status(self, status):
        """Set WiFi status and detect changes"""
        if self.wifi_status != status:
            print(f"WiFi status changed: {self.wifi_status} -> {status}")
            self.wifi_status = status
    
    def is_speed_sending_enabled(self):
        """Check if speed sending is currently enabled"""
        return self.sending_speed_enabled
    
    def disable_speed_sending(self):
        """Disable speed sending (safety mechanism)"""
        if self.sending_speed_enabled:
            print("Speed sending disabled - POTI ZERO REQUIRED")
            self.sending_speed_enabled = False
    
    def enable_speed_sending(self):
        """Enable speed sending when safe to do so"""
        if not self.sending_speed_enabled:
            print("Speed sending re-enabled - poti zero request cleared")
            self.sending_speed_enabled = True
    
    def check_speed_enable_condition(self, current_speed):
        """
        Check if speed sending can be re-enabled based on poti position
        
        Args:
            current_speed: Current potentiometer reading
        """
        if not self.sending_speed_enabled and current_speed == 0:
            self.enable_speed_sending()
    
    def handle_direction_change(self):
        """Handle direction change event - requires speed reset"""
        self.disable_speed_sending()
        return "Direction changed - POTI ZERO REQUIRED"
    
    def handle_emergency_stop(self):
        """Handle emergency stop event - requires speed reset"""
        self.disable_speed_sending()
        return "EMERGENCY STOP - POTI ZERO REQUIRED"
    
    def handle_locomotive_change(self):
        """Handle locomotive selection change - requires speed reset"""
        self.disable_speed_sending()
        return "Locomotive changed - POTI ZERO REQUIRED"
    
    def get_system_status(self, rocrail_status):
        """
        Get overall system status for display purposes
        
        Args:
            rocrail_status: Current RocRail connection status
            
        Returns:
            dict: System status information
        """
        return {
            'wifi_connected': self.wifi_status == "connected",
            'rocrail_connected': rocrail_status == "connected",
            'speed_enabled': self.sending_speed_enabled,
            'system_ready': (self.wifi_status == "connected" and 
                           rocrail_status == "connected" and 
                           self.sending_speed_enabled)
        }
    
    def has_status_changed(self, rocrail_status):
        """
        Check if any status has changed since last call
        
        Args:
            rocrail_status: Current RocRail connection status
            
        Returns:
            bool: True if any status changed
        """
        changed = (
            self._last_wifi_status != self.wifi_status or
            self._last_rocrail_status != rocrail_status or
            self._last_speed_enabled != self.sending_speed_enabled
        )
        
        # Update last known states
        self._last_wifi_status = self.wifi_status
        self._last_rocrail_status = rocrail_status
        self._last_speed_enabled = self.sending_speed_enabled
        
        return changed

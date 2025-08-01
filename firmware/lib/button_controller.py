# controllers/button_controller.py
from machine import Pin
import time

class ButtonController:
    """Klasse zur Verwaltung von Buttons mit Entprellung"""
    
    def __init__(self, pin_num, pull_up=True, debounce_ms=50):
        # Button-Pin konfigurieren
        self.pin = Pin(pin_num, Pin.IN, pull=Pin.PULL_UP if pull_up else Pin.PULL_DOWN)
        self.last_state = self.pin.value()
        self.last_change = time.ticks_ms()
        self.active_level = 0 if pull_up else 1  # Aktiv-Level ist 0 bei Pull-Up, 1 bei Pull-Down
        self.debounce_ms = debounce_ms
    
    def is_pressed(self):
        """Prüft ob Button gedrückt wurde (mit Entprellung)
        
        Returns:
            True wenn Button gerade gedrückt wurde, sonst False
        """
        current_time = time.ticks_ms()
        current_state = self.pin.value()
        
        # Prüfen ob genug Zeit für Entprellung vergangen ist
        if current_time - self.last_change >= self.debounce_ms:
            # Zustandsänderung erkannt
            if current_state != self.last_state:
                self.last_change = current_time
                self.last_state = current_state
                
                # Button wurde gedrückt (Übergang zu active_level)
                if current_state == self.active_level:
                    return True
        
        return False
    
    def is_active(self):
        """Prüft ob Button aktiv ist (gedrückt gehalten)
        
        Returns:
            True wenn Button aktuell gedrückt ist, sonst False
        """
        return self.pin.value() == self.active_level
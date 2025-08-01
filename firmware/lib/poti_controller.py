# controllers/poti_controller.py
from machine import ADC, Pin

class PotiController:
    """Controls and reads from a potentiometer with noise filtering"""
    
    def __init__(self, pin_num=36, filter_size=10, threshold=1):
        # Setup ADC
        self.pot = ADC(Pin(pin_num))
        self.pot.atten(ADC.ATTN_11DB)  # Full range: 3.3v
        
        # Variables for noise filtering
        self.filter_size = filter_size  # Number of samples for moving average
        self.samples = []               # Buffer to store samples
        self.last_value = None          # Last returned value
        self.threshold = threshold      # Minimum change to report a new value
    
    def read(self):
        """
        Read the potentiometer value with noise filtering and normalization.
        Returns False if the value hasn't changed beyond threshold,
        otherwise returns the normalized value (0-100).
        """
        # Read raw value
        raw_value = self.pot.read()
        
        # Add new sample to buffer
        self.samples.append(raw_value)
        
        # Keep only the last filter_size samples
        if len(self.samples) > self.filter_size:
            self.samples.pop(0)
        
        # Calculate average (noise filtering)
        filtered_value = sum(self.samples) / len(self.samples)
        
        # Normalize to 0-100 range
        normalized_value = int((filtered_value / 4096) * 100)
        
        # Check if value has changed beyond threshold
        if self.last_value is None or abs(normalized_value - self.last_value) >= self.threshold:
            self.last_value = normalized_value
            return normalized_value
        
        return normalized_value
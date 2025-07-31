import time

class IntervalTimer:
    """Helper class for managing time intervals in milliseconds"""
    
    def __init__(self):
        self.last_times = {}  # Stores last execution times for different timers
    
    def is_ready(self, timer_name, interval_ms):
        """Checks if a time interval has elapsed
        
        Args:
            timer_name: Name of the timer
            interval_ms: Interval in milliseconds
            
        Returns:
            True if interval has elapsed, False otherwise
        """
        current_time = time.ticks_ms()  # Get current time in milliseconds
        
        # Initialize timer if it doesn't exist
        if timer_name not in self.last_times:
            self.last_times[timer_name] = 0
        
        # Check if interval has elapsed (using ticks_diff for proper overflow handling)
        if time.ticks_diff(current_time, self.last_times[timer_name]) >= interval_ms:
            # Update timer
            self.last_times[timer_name] = current_time
            return True
        
        return False
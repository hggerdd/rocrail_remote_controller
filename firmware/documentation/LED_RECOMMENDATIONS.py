"""
LED Status Recommendations for AsyncIO Implementation

The asyncio implementation may require LED timing adjustments due to different 
update patterns compared to the legacy polling system.

Recommended LED Updates:
"""

# LED brightness adjustments for better asyncio timing
LED_BRIGHT = 200  # Reduced from 255 for better visibility
LED_DIM_HIGH = 60  # Increased from 50 for better dim states
LED_DIM_LOW = 15   # Reduced from 20 for better contrast
LED_DIM_MIN = 5    # New minimum for subtle effects

# Blinking timing adjustments for asyncio
NEOPIXEL_BLINK_INTERVAL_FAST = 300  # ms - faster blinking for critical states
NEOPIXEL_BLINK_INTERVAL_NORMAL = 500  # ms - normal blinking (current default)
NEOPIXEL_BLINK_INTERVAL_SLOW = 800   # ms - slower blinking for stable states

# LED update frequency for async tasks
LED_UPDATE_INTERVAL = 100  # ms - how often LED task runs
LED_REFRESH_INTERVAL = 2000  # ms - how often to refresh LEDs (prevent lockup)

"""
Implementation Notes:
1. AsyncIO LED updates are more consistent than polling-based updates
2. Blink timing may appear different due to event-driven updates vs timer-based
3. Consider adjusting brightness levels for better battery life in async mode
4. The async LED controller includes automatic refresh to prevent RMT lockups
"""

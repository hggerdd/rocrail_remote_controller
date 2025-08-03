# config.py - Configuration settings

# WiFi settings
WIFI_SSID = "Bbox-328C6AED"
WIFI_PASSWORD = "1DF9524DDC396399F7FD71C7F62E9A"

# RocRail settings
ROCRAIL_HOST = "192.168.1.27"
ROCRAIL_PORT = 8051

# Default locomotive
DEFAULT_LOCO_ID = "BR103"

# Locomotive management
LOCO_LIST_FILE = "loco_list.txt"
LOCO_QUERY_INTERVAL = 30000  # Query locomotives every 30 seconds
LOCO_QUERY_TIMEOUT = 10000   # Timeout for locomotive query response (10 seconds)
MAX_LOCOMOTIVES = 5  # Limited by NeoPixel LEDs 1-5

# Timing intervals (ms)
WIFI_CHECK_INTERVAL = 15500
ROCRAIL_CHECK_INTERVAL = 13200
LOCO_CHECK_INTERVAL = 100
POTI_UPDATE_INTERVAL = 50
BUTTON_CHECK_INTERVAL = 10
SPEED_UPDATE_INTERVAL = 333

# Hardware pins
POTI_PIN = 36
NEOPIXEL_PIN = 5  # Pin for 6 NeoPixel LEDs

# Button pins
LIGHT_BUTTON_PIN = 34    # Beleuchtung ein/aus
WHISTLE_BUTTON_PIN = 32  # Pfeife betätigen
DIRECTION_BUTTON_PIN = 33  # Fahrtrichtung umkehren
SOUND_BUTTON_PIN = 35    # Geräusche ein/aus
EMERGENCY_BUTTON_PIN = 39  # Nothalt für die gewählte Lok

# Potentiometer settings
POTI_FILTER_SIZE = 3
POTI_THRESHOLD = 1

# NeoPixel settings
NEOPIXEL_COUNT = 10
NEOPIXEL_BLINK_INTERVAL = 500  # ms for blinking effect

# LED assignments for 10 NeoPixel setup
LED_WIFI = 0          # WiFi status indicator
LED_ROCRAIL = 1       # RocRail connection status ("RR")
LED_DIR_LEFT = 2      # Direction indicator "<" (true)
LED_DIR_RIGHT = 3     # Direction indicator ">" (false)
LED_ACTIVITY = 4      # Activity indicator
LED_LOCO_START = 5    # First locomotive LED (LEDs 5-9 = locos 1-5)
LED_LOCO_END = 9      # Last locomotive LED
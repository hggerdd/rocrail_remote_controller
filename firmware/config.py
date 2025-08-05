# config.py - Application configuration settings
# (Non-hardware settings from rocrail_config.py)

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
WIFI_RECONNECT_MAX_RETRIES = 5  # Maximum retries for WiFi reconnection
ROCRAIL_CHECK_INTERVAL = 13200

# RocRail reconnection settings
RECONNECT_DELAY_FAST = 3000         # 3s für erste Versuche (weniger aggressiv)
RECONNECT_DELAY_SLOW = 8000         # 8s für spätere Versuche  
RECONNECT_FAST_ATTEMPTS = 3         # nur 3x schnell, dann langsamer
RECONNECT_UNLIMITED = True          # Niemals aufgeben
SOCKET_TIMEOUT = 10                 # Socket timeout in seconds (erhöht)

LOCO_CHECK_INTERVAL = 100
POTI_UPDATE_INTERVAL = 50
BUTTON_CHECK_INTERVAL = 10
SPEED_UPDATE_INTERVAL = 333

# Potentiometer settings
POTI_FILTER_SIZE = 3
POTI_THRESHOLD = 1
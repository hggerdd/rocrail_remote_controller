# config.py - Configuration settings

# WiFi settings
WIFI_SSID = "Bbox-328C6AED"
WIFI_PASSWORD = "1DF9524DDC396399F7FD71C7F62E9A"

# RocRail settings
ROCRAIL_HOST = "192.168.1.27"
ROCRAIL_PORT = 8051

# Default locomotive
DEFAULT_LOCO_ID = "BR103"

# Timing intervals (ms)
WIFI_CHECK_INTERVAL = 15500
ROCRAIL_CHECK_INTERVAL = 13200
LOCO_CHECK_INTERVAL = 100
POTI_UPDATE_INTERVAL = 50
BUTTON_CHECK_INTERVAL = 10
SPEED_UPDATE_INTERVAL = 333

# Hardware pins
LED_PIN = 5
POTI_PIN = 36

# Button pins
LIGHT_BUTTON_PIN = 34    # Beleuchtung ein/aus
WHISTLE_BUTTON_PIN = 32  # Pfeife betätigen
DIRECTION_BUTTON_PIN = 33  # Fahrtrichtung umkehren
SOUND_BUTTON_PIN = 35    # Geräusche ein/aus
EMERGENCY_BUTTON_PIN = 39  # Nothalt für die gewählte Lok

# Potentiometer settings
POTI_FILTER_SIZE = 3
POTI_THRESHOLD = 1
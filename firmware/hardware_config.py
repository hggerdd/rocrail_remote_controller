# hardware_config.py - Zentrale Hardware-Konfiguration
# Einheitliche Pin-Definitionen für ESP32 Locomotive Controller

# Button Pins (funktionierend aus btn_config.py)
BTN_NOTHALT = 17          # Red emergency/config button
BTN_RICHTUNGSWECHEL = 19  # Green direction toggle
BTN_GELB = 22             # Yellow sound/horn button
BTN_BLAU = 23             # Blue light toggle button
BTN_MITTE_UP = 18         # Black up - next locomotive
BTN_MITTE_DOWN = 21       # Black down - previous locomotive

# Analog Inputs (funktionierend aus btn_config.py)
ADC_GESCHWINDIGKEIT = 34  # Speed potentiometer

# NeoPixel Configuration (aus rocrail_config.py - 10 LEDs physisch vorhanden)
NEOPIXEL_PIN = 5          # NeoPixel data pin
NEOPIXEL_COUNT = 10       # Total number of NeoPixel LEDs

# LED Assignments for 10 NeoPixel setup (aus rocrail_config.py)
LED_WIFI = 0              # WiFi status indicator
LED_ROCRAIL = 1           # RocRail connection status ("RR")
LED_DIR_LEFT = 2          # Direction indicator "<" (true/forward)
LED_DIR_RIGHT = 3         # Direction indicator ">" (false/reverse)
LED_ACTIVITY = 4          # Activity indicator / Poti zero request
LED_LOCO_START = 5        # First locomotive LED (LEDs 5-9 = locos 1-5)
LED_LOCO_END = 9          # Last locomotive LED

# NeoPixel Settings
NEOPIXEL_BLINK_INTERVAL = 500  # ms for blinking effect (base interval, may be adjusted in code)

# Backward compatibility aliases (für schrittweise Migration)
POTI_PIN = ADC_GESCHWINDIGKEIT  # Alias für rocrail_config.py compatibility

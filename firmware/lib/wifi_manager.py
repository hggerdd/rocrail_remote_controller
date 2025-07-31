# network/wifi_manager.py
import network
import time
from machine import Pin

class WifiManager:
    """Manages WiFi connections"""
    
    def __init__(self, ssid, password, led_pin=5, max_retries=10, retry_delay=5):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.led = Pin(led_pin, Pin.OUT)  # Onboard LED for status
        self.last_check_time = 0
    
    def scan_for_network(self):
        """Searches for the configured WiFi network"""
        print("Searching for WiFi:", self.ssid)
        self.wlan.active(True)
        networks = self.wlan.scan()
        
        for net in networks:
            ssid = net[0].decode('utf-8') if isinstance(net[0], bytes) else net[0]
            if ssid == self.ssid:
                print(f"WiFi '{self.ssid}' found!")
                return True
                
        print(f"WiFi '{self.ssid}' not found.")
        return False
    
    def connect(self):
        """Connects to the WiFi network"""
        if not self.wlan.isconnected():
            print('Connecting to WiFi:', self.ssid)
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            
            retries = 0
            while not self.wlan.isconnected() and retries < self.max_retries:
                self.led.value(not self.led.value())  # Blink LED
                time.sleep(self.retry_delay)
                retries += 1
                print(f'Connection attempt {retries}/{self.max_retries}')
            
            if self.wlan.isconnected():
                print('WiFi connected!')
                print(f'IP: {self.wlan.ifconfig()[0]}')
                self.led.value(1)  # LED on when connection successful
                self.last_check_time = time.time()
                return True
            else:
                print('WiFi connection failed!')
                self.led.value(0)  # LED off on connection error
                return False
        else:
            print('Already connected to WiFi')
            print(f'IP: {self.wlan.ifconfig()[0]}')
            self.led.value(1)
            self.last_check_time = time.time()
            return True
    
    def check_connection(self, force=False):
        """Checks WiFi connection and restores if necessary
        
        Args:
            force: If True, check is performed immediately regardless of last check time
        
        Returns:
            True if connected, False otherwise
        """
        if not self.wlan.isconnected():
            print('WiFi connection lost! Attempting to reconnect...')
            return self.connect()
        else:
            print('WiFi connection OK')
            self.led.value(1)  # LED on when connection active
            return True
    
    def disconnect(self):
        """Disconnects from WiFi"""
        if self.wlan.isconnected():
            self.wlan.disconnect()
            self.wlan.active(False)
            print('WiFi disconnected')
            self.led.value(0)
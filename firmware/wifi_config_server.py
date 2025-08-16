import network
import socket
import time
import machine
import gc
import json
from neopixel import NeoPixel
from machine import Pin, ADC
from hardware_config import ADC_GESCHWINDIGKEIT, NEOPIXEL_PIN, NEOPIXEL_COUNT

# Configuration
AP_SSID = "ESP_Config"
AP_PASSWORD = "config123"

class NeoPixelStatus:
    def __init__(self, pin=NEOPIXEL_PIN, count=NEOPIXEL_COUNT):
        """Initialize NeoPixel LEDs for status indication"""
        self.np = NeoPixel(machine.Pin(pin), count)
        self.count = count
        self.connection_toggle = False  # For toggling connection indicator
        
        # LED positions
        self.LED_CONFIG = 0      # Configuration started
        self.LED_AP = 1          # AP status  
        self.LED_ACTIVITY = 2    # Connection activity
        self.LED_ERROR = 3       # Error status
        self.LED_WIFI = 4        # WiFi connection status
        self.LED_TEMP = 5        # Temperature status
        
        # Colors (R, G, B)
        self.COLOR_OFF = (0, 0, 0)
        self.COLOR_RED = (255, 0, 0)
        self.COLOR_GREEN = (0, 255, 0)
        self.COLOR_BLUE = (0, 0, 255)
        self.COLOR_YELLOW = (255, 255, 0)
        self.COLOR_ORANGE = (255, 165, 0)
        self.COLOR_PURPLE = (128, 0, 128)
        
        # ADC configuration for brightness control
        self.brightness_factor = 1.0  # Default full brightness
        self.last_brightness_read = 0
        self.last_brightness_factor = 1.0  # Track changes
        self.readings = []
        self.AVERAGE_SAMPLES = 5  # Reduced for faster response
        self.MIN_VALUE = 1310  # Poti calibration from adc_test.py
        self.MAX_VALUE = 2360
        
        # Store current LED states (desired colors without brightness applied)
        self.led_states = [self.COLOR_OFF] * count
        
        # Initialize ADC with error handling
        try:
            self.adc = ADC(Pin(ADC_GESCHWINDIGKEIT))
            self.adc.atten(ADC.ATTN_11DB)  # 0-3.3V range
            print(f"ADC initialized on GPIO{ADC_GESCHWINDIGKEIT} for brightness control")
        except Exception as e:
            print(f"Warning: ADC initialization failed: {e} - Using full brightness")
            self.adc = None
        
        self.clear_all()
        print("NeoPixel initialized with", count, "LEDs on pin", pin)
    
    def clear_all(self):
        """Turn off all LEDs"""
        for i in range(self.count):
            self.led_states[i] = self.COLOR_OFF
        self.update_all_leds()
    
    def update_all_leds(self):
        """Update all LEDs with current brightness factor"""
        for i in range(self.count):
            brightness_color = self.apply_brightness(self.led_states[i])
            self.np[i] = brightness_color
        self.np.write()
    
    def read_brightness(self):
        """Read brightness from potentiometer and update LEDs if changed"""
        current_time = time.ticks_ms()
        
        # Read every 50ms for responsive updates
        if time.ticks_diff(current_time, self.last_brightness_read) < 50:
            return self.brightness_factor
        
        self.last_brightness_read = current_time
        
        if self.adc is None:
            return 1.0  # Fallback to full brightness
        
        try:
            # Read ADC value
            raw_value = self.adc.read()
            
            # Gleitender Mittelwert (rolling average)
            self.readings.append(raw_value)
            if len(self.readings) > self.AVERAGE_SAMPLES:
                self.readings.pop(0)
            avg_value = sum(self.readings) // len(self.readings)
            
            # Map to 0-100 range
            if avg_value <= self.MIN_VALUE:
                mapped_value = 0
            elif avg_value >= self.MAX_VALUE:
                mapped_value = 100
            else:
                mapped_value = int((avg_value - self.MIN_VALUE) / (self.MAX_VALUE - self.MIN_VALUE) * 100)
            
            # Convert to brightness factor (1% minimum for visibility, 100% maximum)
            new_brightness_factor = max(0.01, mapped_value / 100.0)
            
            # Check if brightness changed significantly (more responsive threshold)
            if abs(new_brightness_factor - self.last_brightness_factor) > 0.01:  # 1% threshold for faster response
                self.brightness_factor = new_brightness_factor
                self.last_brightness_factor = new_brightness_factor
                # Immediately update all LEDs with new brightness
                self.update_all_leds()
                print(f"Brightness updated: {int(mapped_value)}% (factor: {self.brightness_factor:.2f})")
            
            return self.brightness_factor
            
        except Exception as e:
            print(f"Warning: ADC read failed: {e} - Using previous brightness")
            return self.brightness_factor
    
    def apply_brightness(self, color):
        """Apply current brightness factor to RGB color"""
        if color == self.COLOR_OFF:
            return color  # Don't modify OFF color
        
        r, g, b = color
        # Apply brightness factor and ensure values stay in 0-255 range
        r = max(0, min(255, int(r * self.brightness_factor)))
        g = max(0, min(255, int(g * self.brightness_factor)))
        b = max(0, min(255, int(b * self.brightness_factor)))
        return (r, g, b)
    
    def set_led(self, index, color):
        """Set specific LED color with brightness control"""
        if 0 <= index < self.count:
            # Store the desired color state
            self.led_states[index] = color
            # Apply brightness and update LEDs
            self.update_all_leds()
    
    def config_started(self):
        """Set configuration started indicator (LED 0 green)"""
        self.set_led(self.LED_CONFIG, self.COLOR_GREEN)
        print("LED: Configuration started (green)")
    
    def ap_status(self, active):
        """Set AP status (LED 1: red=inactive, green=active)"""
        color = self.COLOR_GREEN if active else self.COLOR_RED
        self.set_led(self.LED_AP, color)
        status = "active" if active else "inactive"
        print(f"LED: AP {status} ({'green' if active else 'red'})")
    
    def connection_activity(self):
        """Toggle connection activity indicator (LED 2: blue/yellow)"""
        self.connection_toggle = not self.connection_toggle
        color = self.COLOR_BLUE if self.connection_toggle else self.COLOR_YELLOW
        self.set_led(self.LED_ACTIVITY, color)
    
    def error_status(self, error=True):
        """Set error status (LED 3: red=error, off=no error)"""
        color = self.COLOR_RED if error else self.COLOR_OFF
        self.set_led(self.LED_ERROR, color)
        if error:
            print("LED: Error status (red)")
    
    def wifi_status(self, connected):
        """Set WiFi connection status (LED 4: green=connected, off=disconnected)"""
        color = self.COLOR_GREEN if connected else self.COLOR_OFF
        self.set_led(self.LED_WIFI, color)
        status = "connected" if connected else "disconnected"
        print(f"LED: WiFi {status} ({'green' if connected else 'off'})")
    
    def temperature_status(self, temp_celsius):
        """Set temperature status (LED 5: green<30°C, yellow 30-50°C, red>50°C)"""
        if temp_celsius is None:
            color = self.COLOR_OFF
        elif temp_celsius < 30:
            color = self.COLOR_GREEN
        elif temp_celsius < 50:
            color = self.COLOR_YELLOW
        else:
            color = self.COLOR_RED
        
        self.set_led(self.LED_TEMP, color)

class WiFiConfigAPI:
    def __init__(self):
        self.ap = None
        self.socket = None
        # Initialize NeoPixel LEDs
        self.leds = NeoPixelStatus()
        
        # Performance optimizations - cache data
        self._network_cache = None
        self._network_cache_time = 0
        self._config_cache = None
        self._config_cache_time = 0
        self._rocrail_cache = None
        self._rocrail_cache_time = 0
        
        # Initialize logging system
        self.log_file = "error_log.txt"
        self._clear_log_file()
    
    def _clear_log_file(self):
        """Clear the log file at startup"""
        try:
            import os
            os.remove(self.log_file)
            print("Previous error log cleared")
        except:
            pass  # File doesn't exist, which is fine
    
    def _log_error(self, error_msg, exception=None):
        """Log error message to file and console with LED indicator"""
        import time
        timestamp = time.localtime()
        formatted_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            timestamp[0], timestamp[1], timestamp[2], 
            timestamp[3], timestamp[4], timestamp[5]
        )
        
        # Format the complete error message
        if exception:
            full_msg = f"[{formatted_time}] ERROR: {error_msg} - Exception: {str(exception)}"
        else:
            full_msg = f"[{formatted_time}] ERROR: {error_msg}"
        
        # Print to console
        print(full_msg)
        
        # Write to log file
        try:
            with open(self.log_file, "a") as f:
                f.write(full_msg + "\n")
        except Exception as log_e:
            print(f"Failed to write to log file: {log_e}")
        
        # Set LED error status
        self.leds.error_status(True)
        
        return full_msg
        
    def create_ap(self):
        """Create WiFi Access Point"""
        try:
            self.ap = network.WLAN(network.AP_IF)
            self.ap.active(True)
            
            if AP_PASSWORD:
                self.ap.config(essid=AP_SSID, password=AP_PASSWORD)
            else:
                self.ap.config(essid=AP_SSID)
            
            # Set AP status to inactive initially
            self.leds.ap_status(False)
            
            timeout = 10  # 10 second timeout
            while not self.ap.active() and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
            
            if not self.ap.active():
                self._log_error("Access Point failed to activate within timeout")
                return None
            
            # AP is now active
            self.leds.ap_status(True)
            
            print(f"AP: {AP_SSID}")
            if AP_PASSWORD:
                print(f"Password: {AP_PASSWORD}")
            print(f"IP: {self.ap.ifconfig()[0]}")
            return self.ap
            
        except Exception as e:
            self._log_error("Failed to create Access Point", e)
            return None
    
    def get_device_info(self):
        """Get device information including temperature"""
        try:
            import sys
            platform = sys.platform
            if 'esp32' in platform:
                device = 'ESP32'
            elif 'esp8266' in platform:
                device = 'ESP8266'
            elif 'rp2' in platform:
                device = 'Raspberry Pi Pico'
            else:
                device = platform.upper()
        except Exception as e:
            self._log_error("Failed to detect device platform", e)
            device = 'Unknown Device'
        
        try:
            gc.collect()
            memory = gc.mem_free() // 1024
        except Exception as e:
            self._log_error("Failed to get memory information", e)
            memory = 0
        
        # Get chip temperature and update LED
        temperature = self.get_chip_temperature()
        if temperature is not None:
            self.leds.temperature_status(temperature)
            
        return device, memory, temperature
    
    def get_chip_temperature(self):
        """Get internal chip temperature in Celsius"""
        try:
            import sys
            platform = sys.platform
            
            if 'esp32' in platform:
                # ESP32 internal temperature sensor
                import esp32
                # raw_temperature() returns Fahrenheit
                temp_f = esp32.raw_temperature()
                temp_c = (temp_f - 32) * 5.0 / 9.0
                return round(temp_c, 1)
            
            elif 'esp8266' in platform:
                # ESP8266 internal temperature sensor
                try:
                    import esp
                    # ESP8266 might have different API
                    temp_f = esp.temperature()
                    temp_c = (temp_f - 32) * 5.0 / 9.0
                    return round(temp_c, 1)
                except Exception as e:
                    self._log_error("ESP8266 temperature sensor unavailable", e)
                    return None
            
            elif 'rp2' in platform:
                # Raspberry Pi Pico internal temperature
                try:
                    from machine import ADC
                    sensor_temp = ADC(4)  # Temperature sensor on ADC channel 4
                    reading = sensor_temp.read_u16() * 3.3 / (65535)
                    temperature = 27 - (reading - 0.706) / 0.001721
                    return round(temperature, 1)
                except Exception as e:
                    self._log_error("Raspberry Pi Pico temperature sensor failed", e)
                    return None
            
            else:
                self._log_error(f"Temperature sensor not supported for platform: {platform}")
                return None
                
        except Exception as e:
            self._log_error("Critical failure reading chip temperature", e)
            return None
    
    def scan_networks(self):
        """Scan for WiFi networks with signal strength - CACHED"""
        import time
        current_time = time.time()
        
        # Use cache if less than 30 seconds old
        if self._network_cache and (current_time - self._network_cache_time) < 30:
            print("Using cached network scan")
            return self._network_cache
        
        print("Performing fresh network scan...")
        sta = network.WLAN(network.STA_IF)
        
        try:
            sta.active(True)
            
            # Faster scan with shorter timeout
            networks = sta.scan()
            network_list = []
            seen_ssids = set()
            
            for net in networks:
                try:
                    ssid = net[0].decode('utf-8')
                    if ssid and ssid not in seen_ssids and len(network_list) < 20:  # Limit to 20 networks
                        network_info = {
                            'ssid': ssid,
                            'rssi': net[3],  # Signal strength
                            'security': net[4]  # Security type
                        }
                        network_list.append(network_info)
                        seen_ssids.add(ssid)
                except Exception as e:
                    print(f"Warning: Failed to decode network SSID: {e}")
                    continue
            
            sta.active(False)
            # Sort by signal strength (higher RSSI = better signal)
            result = sorted(network_list, key=lambda x: x['rssi'], reverse=True)
            
            # Cache the result
            self._network_cache = result
            self._network_cache_time = current_time
            print(f"Cached {len(result)} networks")
            
            return result
            
        except Exception as e:
            self._log_error("WiFi network scan failed - check antenna/WiFi module", e)
            try:
                sta.active(False)
            except:
                pass
            return self._network_cache or []  # Return cached data on error
    
    def load_config(self):
        """Load WiFi configuration with failure count - LEGACY for compatibility"""
        networks = self.load_wifi_networks()
        if networks:
            # Return first network for compatibility
            net = networks[0]
            return net['ssid'], net['password'], net['failures']
        return "", "", 0
    
    def load_wifi_networks(self):
        """Load multiple WiFi networks configuration - CACHED"""
        import time
        current_time = time.time()
        
        # Use cache if less than 5 seconds old
        if self._config_cache and (current_time - self._config_cache_time) < 5:
            return self._config_cache
        
        try:
            with open("wifi_networks.txt", "r") as f:
                import json
                networks = json.loads(f.read())
                print("Loaded", len(networks), "networks from file")
                
                # Cache the result
                self._config_cache = networks
                self._config_cache_time = current_time
                return networks
                
        except OSError as e:
            self._log_error("WiFi networks file not found or corrupted - trying legacy format", e)
            # Try legacy format
            try:
                with open("wifi_config.txt", "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        ssid = lines[0].strip()
                        password = lines[1].strip()
                        failures = 0
                        if len(lines) >= 3:
                            try:
                                failures = int(lines[2].strip())
                            except:
                                failures = 0
                        legacy_network = [{"ssid": ssid, "password": password, "failures": failures}]
                        print("Loaded legacy network:", ssid)
                        
                        # Cache the result
                        self._config_cache = legacy_network
                        self._config_cache_time = current_time
                        return legacy_network
            except Exception as legacy_error:
                self._log_error("Legacy WiFi config file also failed to load", legacy_error)
                
        except Exception as e:
            self._log_error("Critical error loading WiFi configuration files", e)
        
        print("No networks found, returning empty list")
        empty_list = []
        self._config_cache = empty_list
        self._config_cache_time = current_time
        return empty_list
    
    def save_wifi_networks(self, networks):
        """Save multiple WiFi networks configuration"""
        try:
            import json
            print("Saving", len(networks), "networks to file...")
            with open("wifi_networks.txt", "w") as f:
                f.write(json.dumps(networks))
            print("Networks saved successfully")
            
            # Invalidate cache
            self._config_cache = None
            self._config_cache_time = 0
            
            return True
        except OSError as e:
            self._log_error("Failed to save networks - filesystem may be read-only or full", e)
            return False
        except Exception as e:
            self._log_error("Critical error saving WiFi networks configuration", e)
            return False
    
    def load_rocrail_config(self):
        """Load Rocrail server configuration from config.py - CACHED"""
        import time
        current_time = time.time()

        # Use cache if less than 10 seconds old
        if self._rocrail_cache and (current_time - self._rocrail_cache_time) < 10:
            return self._rocrail_cache

        ip = ""
        port = 8051  # Default port
        try:
            with open("config.py", "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ROCRAIL_HOST"):
                        # Extract value between quotes
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            ip_val = parts[1].strip()
                            if ip_val.startswith('"') and ip_val.endswith('"'):
                                ip = ip_val[1:-1]
                            elif ip_val.startswith("'") and ip_val.endswith("'"):
                                ip = ip_val[1:-1]
                            else:
                                ip = ip_val
                    elif line.startswith("ROCRAIL_PORT"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            try:
                                port = int(parts[1].strip())
                            except:
                                port = 8051
            result = (ip, port)
            self._rocrail_cache = result
            self._rocrail_cache_time = current_time
            return result
        except Exception as e:
            self._log_error("Failed to load Rocrail configuration from config.py - using defaults", e)

        result = ("", 8051)  # Default values
        self._rocrail_cache = result
        self._rocrail_cache_time = current_time
        return result
    
    def save_rocrail_config(self, ip, port):
        """Save Rocrail server configuration to config.py by updating ROCRAIL_HOST and ROCRAIL_PORT"""
        try:
            config_path = "config.py"
            with open(config_path, "r") as f:
                lines = f.readlines()
            new_lines = []
            found_host = False
            found_port = False
            for line in lines:
                if line.strip().startswith("ROCRAIL_HOST"):
                    new_lines.append(f'ROCRAIL_HOST = "{ip}"\n')
                    found_host = True
                    print(f"[save_rocrail_config] Updated ROCRAIL_HOST to '{ip}'")
                elif line.strip().startswith("ROCRAIL_PORT"):
                    new_lines.append(f'ROCRAIL_PORT = {port}\n')
                    found_port = True
                    print(f"[save_rocrail_config] Updated ROCRAIL_PORT to {port}")
                else:
                    new_lines.append(line)
            if not found_host or not found_port:
                msg = "[save_rocrail_config] ERROR: ROCRAIL_HOST or ROCRAIL_PORT not found in config.py"
                print(msg)
                self._log_error(msg)
                self.leds.error_status(True)
                return False
            with open(config_path, "w") as f:
                f.write("".join(new_lines))
            print("[save_rocrail_config] config.py written successfully.")

            # Invalidate cache
            self._rocrail_cache = None
            self._rocrail_cache_time = 0

            self.leds.error_status(False)
            return True
        except Exception as e:
            self._log_error("Failed to save Rocrail configuration - check filesystem permissions", e)
            self.leds.error_status(True)
            return False
    
    def test_connection(self, ssid, password):
        """Test WiFi connection"""
        sta = network.WLAN(network.STA_IF)
        
        try:
            sta.active(True)
            
            if sta.isconnected():
                sta.disconnect()
                time.sleep(1)
            
            print(f"Testing connection to: {ssid}")
            sta.connect(ssid, password)
            timeout = 15
            while timeout > 0 and not sta.isconnected():
                time.sleep(1)
                timeout -= 1
            
            if sta.isconnected():
                ip = sta.ifconfig()[0]
                self.leds.wifi_status(True)  # Connected
                sta.active(False)
                print(f"Connection test successful: {ip}")
                return True, ip
            else:
                self._log_error(f"WiFi connection test failed for '{ssid}' - timeout after 15 seconds")
                self.leds.wifi_status(False)  # Failed to connect
                sta.active(False)
                return False, None
                
        except Exception as e:
            self._log_error(f"WiFi connection test failed for '{ssid}' - check credentials/signal", e)
            self.leds.wifi_status(False)
            try:
                sta.active(False)
            except:
                pass
            return False, None
    
    def serve_file(self, filename):
        """Serve static files from frontend folder"""
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.ico': 'image/x-icon'
        }
        
        try:
            # Map files to frontend folder
            filepath = f"frontend/{filename}"
            print("Serving file: ", filepath)
            
            # Determine content type
            content_type = 'text/plain'
            for ext, ct in content_types.items():
                if filename.endswith(ext):
                    content_type = ct
                    break
            
            # Get file size first
            import os
            file_size = os.stat(filepath)[6]  # Get file size
            print(f"File size: {file_size} bytes")
            
            return content_type, filepath, file_size
            
        except OSError as e:
            self._log_error(f"Static file not found: {filepath} - check frontend folder exists", e)
            return None, None, 0
        except Exception as e:
            self._log_error(f"Failed to access static file: {filepath}", e)
            return None, None, 0
    
    def stream_file_response(self, client, filepath, content_type, file_size):
        """Stream file in chunks with robust connection handling"""
        try:
            # Log memory before transfer
            gc.collect()
            mem_free_start = gc.mem_free()
            print(f"Starting file transfer: {filepath} ({file_size} bytes), free memory: {mem_free_start} bytes")
            
            # Set adaptive timeout based on file size
            timeout = min(15, max(5, file_size // 1000))  # 5-15s based on file size
            client.settimeout(timeout)
            print(f"Set client timeout: {timeout}s for {file_size} bytes")
            
            # Send HTTP headers first
            response_header = f"HTTP/1.1 200 OK\r\n"
            response_header += f"Content-Type: {content_type}\r\n"
            response_header += f"Content-Length: {file_size}\r\n"
            response_header += "Cache-Control: max-age=3600\r\n"  # Reduced cache time
            response_header += "Connection: close\r\n\r\n"
            
            # Verify client connection before sending headers
            try:
                client.send(response_header.encode())
            except OSError as e:
                print(f"Client disconnected before headers: {e}")
                return False
            
            # Stream file with smaller chunks for better responsiveness
            CHUNK_SIZE = 1024  # Smaller chunks for better error detection
            bytes_sent = 0
            consecutive_errors = 0
            
            with open(filepath, 'rb') as f:
                while bytes_sent < file_size:
                    # Check for connection before each chunk
                    if consecutive_errors > 3:
                        print(f"Too many consecutive send errors, aborting transfer")
                        break
                        
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    try:
                        # Send chunk with immediate error detection
                        sent = client.send(chunk)
                        if sent == 0:  # Socket closed
                            print(f"Socket closed by client at {bytes_sent}/{file_size} bytes")
                            break
                            
                        bytes_sent += len(chunk)
                        consecutive_errors = 0  # Reset error count on success
                        
                        # Quick brightness update every 4KB 
                        if bytes_sent % (CHUNK_SIZE * 4) == 0:
                            self.leds.read_brightness()
                            
                    except OSError as e:
                        consecutive_errors += 1
                        if e.args[0] in [32, 104, 128]:  # EPIPE, ECONNRESET, ENOTCONN
                            print(f"Client connection lost: {e.args[0]} at {bytes_sent}/{file_size} bytes")
                            break
                        elif e.args[0] in [11, 110, 116]:  # EAGAIN, ETIMEDOUT  
                            print(f"Send timeout/retry: {e.args[0]}, retrying...")
                            time.sleep_ms(10)  # Brief pause before retry
                            continue
                        else:
                            print(f"Unexpected send error: {e}")
                            break
            
            # Log final status
            success = bytes_sent == file_size
            status = "complete" if success else "incomplete" 
            gc.collect()
            mem_free_end = gc.mem_free()
            print(f"File transfer {status}: {bytes_sent}/{file_size} bytes, free memory: {mem_free_end} bytes")
            return success
            
        except Exception as e:
            self._log_error(f"Failed to stream file: {filepath}", e)
            return False
    
    def json_response(self, data, status=200):
        """Create JSON response"""
        response = f"HTTP/1.1 {status} OK\r\n"
        response += "Content-Type: application/json\r\n"
        response += "Access-Control-Allow-Origin: *\r\n"
        response += "Connection: close\r\n\r\n"
        response += json.dumps(data)
        return response
    
    def file_response(self, content, content_type):
        """Create file response (kept for backward compatibility, but not used)"""
        response = f"HTTP/1.1 200 OK\r\n"
        response += f"Content-Type: {content_type}\r\n"
        response += "Cache-Control: max-age=86400\r\n"  # Cache for 1 day
        response += "Connection: close\r\n\r\n"
        response += content
        return response
    
    def parse_json_body(self, request):
        """Parse JSON from POST request"""
        try:
            lines = request.split('\r\n')
            content_start = False
            json_data = ""
            
            for line in lines:
                if content_start:
                    json_data += line
                elif line == "":
                    content_start = True
            
            return json.loads(json_data) if json_data else {}
            
        except json.JSONDecodeError as e:
            self._log_error("Invalid JSON in request body - check request format", e)
            return {}
        except Exception as e:
            self._log_error("Failed to parse request body", e)
            return {}
    
    def handle_request(self, client, request):
        """Handle HTTP request"""
        try:
            # Indicate connection activity
            self.leds.connection_activity()
            
            lines = request.split('\r\n')
            if not lines:
                client.close()
                return
                
            try:
                method, path, _ = lines[0].split(' ')
            except ValueError as e:
                self._log_error("Malformed HTTP request - invalid request line", e)
                client.send(b"HTTP/1.1 400 Bad Request\r\n\r\n400 - Bad Request")
                client.close()
                return
            
            # Static files from frontend folder
            if method == 'GET' and not path.startswith('/api'):
                # Strip query parameters (e.g., ?_=timestamp for cache busting)
                clean_path = path.split('?')[0]
                
                if clean_path == '/' or clean_path == '/index':
                    filename = 'index.html'
                else:
                    filename = clean_path[1:]  # Remove leading /
                
                content_type, filepath, file_size = self.serve_file(filename)
                
                if filepath:
                    # Set adaptive timeout for file transfers
                    timeout = min(10, max(3, file_size // 2000))  # 3-10s adaptive timeout
                    client.settimeout(timeout)
                    print(f"File transfer timeout set to {timeout}s for {file_size} byte file")
                    success = self.stream_file_response(client, filepath, content_type, file_size)
                    if not success:
                        try:
                            error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\n500 - File Transfer Error"
                            client.send(error_response.encode())
                        except:
                            pass
                else:
                    response = "HTTP/1.1 404 Not Found\r\n\r\n404 - File Not Found"
                    client.send(response.encode())
                
                client.close()
                return
            
            # API endpoints
            if path.startswith('/api'):
                if path == '/api/status':
                    device, memory, temperature = self.get_device_info()
                    networks = self.load_wifi_networks()
                    current_ssid = networks[0]['ssid'] if networks else ""
                    total_failures = sum(net['failures'] for net in networks)
                    rocrail_ip, rocrail_port = self.load_rocrail_config()
                    data = {
                        'device': device,
                        'memory': memory,
                        'temperature': temperature,
                        'ap_ssid': AP_SSID,
                        'current_ssid': current_ssid,
                        'failure_count': total_failures,
                        'rocrail_ip': rocrail_ip,
                        'rocrail_port': rocrail_port,
                        'saved_networks_count': len(networks)
                    }
                    response = self.json_response(data)
                
                elif path == '/api/status-all':
                    # OPTIMIZED: Combined endpoint for all status data
                    print("Getting combined status...")
                    try:
                        device, memory, temperature = self.get_device_info()
                        networks = self.load_wifi_networks()
                        current_ssid = networks[0]['ssid'] if networks else ""
                        total_failures = sum(net['failures'] for net in networks)
                        rocrail_ip, rocrail_port = self.load_rocrail_config()
                        
                        # Get cached scan or quick scan
                        available_networks = self.scan_networks()
                        
                        data = {
                            # Device info
                            'device': device,
                            'memory': memory,
                            'temperature': temperature,
                            'ap_ssid': AP_SSID,
                            
                            # WiFi info
                            'current_ssid': current_ssid,
                            'failure_count': total_failures,
                            'saved_networks_count': len(networks),
                            'saved_networks': networks,
                            
                            # Available networks
                            'available_networks': [net['ssid'] for net in available_networks],
                            'available_networks_detailed': available_networks,
                            
                            # Rocrail info
                            'rocrail_ip': rocrail_ip,
                            'rocrail_port': rocrail_port
                        }
                        response = self.json_response(data)
                    except Exception as e:
                        self._log_error("Failed to collect combined status data", e)
                        data = {'error': 'Failed to get combined status', 'details': str(e)}
                        response = self.json_response(data, 500)
                
                elif path == '/api/networks':
                    networks = self.scan_networks()
                    saved_networks = self.load_wifi_networks()
                    current_ssid = saved_networks[0]['ssid'] if saved_networks else ""
                    total_failures = sum(net['failures'] for net in saved_networks)
                    data = {
                        'networks': [net['ssid'] for net in networks],  # Just SSIDs for compatibility
                        'networks_detailed': networks,  # Full info with signal strength
                        'current_ssid': current_ssid,
                        'failure_count': total_failures
                    }
                    response = self.json_response(data)
                
                elif path == '/api/wifi-networks':
                    if method == 'GET':
                        # Get all saved WiFi networks
                        networks = self.load_wifi_networks()
                        data = {'networks': networks}
                        response = self.json_response(data)
                    
                    elif method == 'POST':
                        # Add new WiFi network
                        json_data = self.parse_json_body(request)
                        ssid = json_data.get('ssid', '').strip()
                        password = json_data.get('password', '')
                        
                        print("Received request to add network:", ssid)
                        
                        if not ssid:
                            data = {'success': False, 'message': 'SSID required'}
                            response = self.json_response(data)
                        else:
                            networks = self.load_wifi_networks()
                            print("Current networks count:", len(networks))
                            
                            # Check if network already exists
                            existing = next((net for net in networks if net['ssid'] == ssid), None)
                            if existing:
                                existing['password'] = password
                                existing['failures'] = 0  # Reset failures when updating
                                message = 'Updated network: ' + ssid
                                print("Updating existing network:", ssid)
                                
                                # Save updated networks
                                if self.save_wifi_networks(networks):
                                    data = {'success': True, 'message': message}
                                    print("Successfully saved networks. New count:", len(networks))
                                else:
                                    data = {'success': False, 'message': 'Failed to save network'}
                                    print("Failed to save networks")
                                response = self.json_response(data)
                                
                            else:
                                if len(networks) >= 5:
                                    data = {'success': False, 'message': 'Maximum 5 networks allowed'}
                                    response = self.json_response(data)
                                    print("Maximum networks reached")
                                else:
                                    networks.append({'ssid': ssid, 'password': password, 'failures': 0})
                                    message = 'Added network: ' + ssid
                                    print("Adding new network:", ssid)
                                    
                                    # Save new networks
                                    if self.save_wifi_networks(networks):
                                        data = {'success': True, 'message': message}
                                        print("Successfully saved networks. New count:", len(networks))
                                    else:
                                        data = {'success': False, 'message': 'Failed to save network'}
                                        print("Failed to save networks")
                                    response = self.json_response(data)
                
                elif path.startswith('/api/wifi-networks/') and method == 'DELETE':
                    # Handle specific network removal
                    ssid_to_remove = path.split('/')[-1]
                    ssid_to_remove = ssid_to_remove.replace('%20', ' ')  # Basic URL decode
                    print("Request to remove network:", ssid_to_remove)
                    
                    networks = self.load_wifi_networks()
                    original_count = len(networks)
                    networks = [net for net in networks if net['ssid'] != ssid_to_remove]
                    
                    if len(networks) < original_count:
                        if self.save_wifi_networks(networks):
                            data = {'success': True, 'message': 'Removed network: ' + ssid_to_remove}
                            print("Successfully removed network:", ssid_to_remove)
                        else:
                            data = {'success': False, 'message': 'Failed to remove network'}
                            print("Failed to save networks after removal")
                    else:
                        data = {'success': False, 'message': 'Network not found'}
                        print("Network not found for removal:", ssid_to_remove)
                    response = self.json_response(data)
                
                elif path == '/api/rocrail':
                    if method == 'GET':
                        # Get current Rocrail configuration
                        ip, port = self.load_rocrail_config()
                        data = {
                            'ip': ip,
                            'port': port
                        }
                        response = self.json_response(data)
                    
                    elif method == 'POST':
                        # Save Rocrail configuration
                        json_data = self.parse_json_body(request)
                        ip = json_data.get('ip', '').strip()
                        port = json_data.get('port', 8051)
                        
                        # Validate port
                        try:
                            port = int(port)
                            if port < 1 or port > 65535:
                                raise ValueError("Port out of range")
                        except:
                            data = {
                                'success': False,
                                'message': 'Invalid port number (1-65535)'
                            }
                            response = self.json_response(data)
                        else:
                            if self.save_rocrail_config(ip, port):
                                data = {
                                    'success': True,
                                    'message': 'Rocrail server configured: ' + ip + ':' + str(port) if ip else 'Rocrail configuration cleared'
                                }
                            else:
                                data = {
                                    'success': False,
                                    'message': 'Failed to save Rocrail configuration'
                                }
                            response = self.json_response(data)
                
                elif path == '/api/configure' and method == 'POST':
                    # Legacy endpoint - add to multi-network system
                    json_data = self.parse_json_body(request)
                    ssid = json_data.get('ssid', '')
                    password = json_data.get('password', '')
                    
                    if ssid:
                        networks = self.load_wifi_networks()
                        # Check if network already exists
                        existing = next((net for net in networks if net['ssid'] == ssid), None)
                        if existing:
                            existing['password'] = password
                            existing['failures'] = 0
                        else:
                            if len(networks) >= 5:
                                # Remove oldest network to make space
                                networks.pop()
                            networks.insert(0, {'ssid': ssid, 'password': password, 'failures': 0})
                        
                        if self.save_wifi_networks(networks):
                            data = {'success': True, 'message': 'Configuration saved for ' + ssid}
                        else:
                            data = {'success': False, 'message': 'Failed to save configuration'}
                    else:
                        data = {'success': False, 'message': 'SSID required'}
                    response = self.json_response(data)
                
                elif path == '/api/test' and method == 'POST':
                    json_data = self.parse_json_body(request)
                    ssid = json_data.get('ssid', '')
                    password = json_data.get('password', '')
                    
                    if ssid:
                        success, ip = self.test_connection(ssid, password)
                        if success:
                            # Save to networks list and move to front
                            networks = self.load_wifi_networks()
                            # Remove if exists
                            networks = [net for net in networks if net['ssid'] != ssid]
                            # Add to front with zero failures
                            networks.insert(0, {'ssid': ssid, 'password': password, 'failures': 0})
                            # Limit to 5 networks
                            if len(networks) > 5:
                                networks = networks[:5]
                            self.save_wifi_networks(networks)
                            
                            data = {'success': True, 'message': '✅ Connected to ' + ssid + '! IP: ' + ip}
                        else:
                            data = {'success': False, 'message': '❌ Failed to connect to ' + ssid}
                    else:
                        data = {'success': False, 'message': 'SSID required'}
                    response = self.json_response(data)
                
                elif path == '/api/forget' and method == 'POST':
                    # Delete all WiFi configurations
                    try:
                        import os
                        try:
                            os.remove("wifi_networks.txt")
                        except:
                            pass
                        try:
                            os.remove("wifi_config.txt")  # Legacy file
                        except:
                            pass
                        # Reset WiFi status LED
                        self.leds.wifi_status(False)
                        data = {'success': True, 'message': 'All WiFi configurations forgotten'}
                    except:
                        data = {'success': True, 'message': 'No configurations to forget'}
                    response = self.json_response(data)
                
                elif path == '/api/restart' and method == 'POST':
                    data = {'success': True, 'message': 'Restarting...'}
                    response = self.json_response(data)
                    client.send(response.encode())
                    client.close()
                    time.sleep(1)
                    machine.reset()
                
                else:
                    data = {'error': 'API endpoint not found'}
                    response = self.json_response(data, 404)
            
            else:
                response = "HTTP/1.1 404 Not Found\r\n\r\n404 - Not Found"
            
            client.send(response.encode())
            client.close()
            
        except Exception as e:
            self._log_error("Critical error handling HTTP request", e)
            try:
                error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\n500 - Internal Server Error"
                client.send(error_response.encode())
                client.close()
            except:
                pass

def start_config_server():
    """Start the configuration server"""
    print("Starting WiFi configuration server...")
    api = WiFiConfigAPI()
    
    # Signal that configuration has started
    api.leds.config_started()
    
    # Create AP with error handling
    if not api.create_ap():
        print("CRITICAL: Failed to create Access Point - cannot continue")
        return
    
    # Create socket with error handling
    try:
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        server_socket = socket.socket()
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(addr)
        server_socket.listen(5)
        # Set socket to non-blocking mode for regular brightness updates
        server_socket.settimeout(0.1)  # 100ms timeout for accept() - more responsive than 50ms
    except Exception as e:
        api._log_error("Failed to create/bind server socket on port 80", e)
        return
    
    print("Server ready!")
    print(f"Connect to: {AP_SSID}")
    if AP_PASSWORD:
        print(f"Password: {AP_PASSWORD}")
    print("Open: http://192.168.4.1")
    print(f"\nBrightness control: Potentiometer on GPIO{ADC_GESCHWINDIGKEIT}")
    print("Brightness update rate: ~20Hz (responsive)")
    print("File serving: Memory-optimized streaming (1KB chunks)")
    print("\nNeoPixel LED Status:")
    print("LED 0 (green): Configuration started")
    print("LED 1 (green): AP active")
    print("LED 2 (blue/yellow): Connection activity")
    print("LED 3 (red): Error status")
    print("LED 4 (green): WiFi connected")
    print("LED 5 (green/yellow/red): Temperature status")
    print("Brightness: Real-time potentiometer control (1%-100%)")
    
    # Clear any startup errors after a short delay
    time.sleep(1)
    api.leds.error_status(False)
    print("Server startup complete - ready for connections")
    
    try:
        while True:
            # Always update brightness from potentiometer first (non-blocking)
            api.leds.read_brightness()
            
            try:
                # Try to accept a client (non-blocking with 100ms timeout)
                client, addr = server_socket.accept()
                client.settimeout(10)  # 10 second timeout for API requests
                request = client.recv(2048).decode()
                if request:
                    # Clear error status when successfully handling requests
                    api.leds.error_status(False)
                    api.handle_request(client, request)
                else:
                    client.close()
            except OSError as e:
                # Handle socket timeouts - these are normal for non-blocking sockets
                # Error codes vary by platform: 110=ETIMEDOUT, 11=EAGAIN, 116=ETIMEDOUT (ESP32)
                if e.args[0] in [110, 11, 116]:  
                    pass  # This is normal, continue to next brightness update
                else:
                    api._log_error("Socket operation failed", e)
            except Exception as e:
                api._log_error("Unexpected error in server loop", e)
            
            # Small delay to prevent busy-waiting CPU, but stay responsive
            time.sleep_ms(10)  # 10ms delay = ~100Hz update rate for brightness
            gc.collect()
            
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        api.leds.clear_all()  # Turn off all LEDs
    except Exception as e:
        api._log_error("Server crashed unexpectedly", e)
    finally:
        try:
            server_socket.close()
        except:
            pass
        try:
            api.ap.active(False)
        except:
            pass
        api.leds.clear_all()  # Turn off all LEDs
        print("Server cleanup completed")

if __name__ == "__main__":
    start_config_server()
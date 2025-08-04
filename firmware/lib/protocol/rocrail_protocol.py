import socket
import time
import _thread

# Debug control - set to False to disable debug output
DEBUG_LOCOMOTIVE_LOADING = True

def debug_print(message):
    """Print debug message if debug mode is enabled"""
    if DEBUG_LOCOMOTIVE_LOADING:
        print(f"[LOCO_DEBUG] {message}")


class RocrailProtocol:
    """
    Handles RocRail protocol communication via TCP socket.
    Manages XML message creation, sending, and receiving.
    """
    
    def __init__(self, loco_list, display_update_callback=None):
        self.loco_list = loco_list
        self.display_update_callback = display_update_callback
        
        # Socket connection variables
        self.socket_client = None
        self.data_callback = None
        self.running = False
        
        # Connection status tracking
        self.rocrail_status = "disconnected"  # States: "disconnected", "connecting", "connected", "lost"
        self.last_rocrail_activity_time = 0
        self.last_rocrail_send_success = True
        
        # XML data handling
        self.xml_buffer = ""
        self.locomotive_query_pending = False
        self.locomotive_query_start_time = 0
        self.locomotives_loaded = False
    
    def get_status(self):
        """Get current RocRail connection status"""
        return self.rocrail_status
    
    def get_last_activity_time(self):
        """Get timestamp of last RocRail activity"""
        return self.last_rocrail_activity_time
    
    def is_query_pending(self):
        """Check if locomotive query is pending"""
        return self.locomotive_query_pending
    
    def get_query_start_time(self):
        """Get timestamp when locomotive query was started"""
        return self.locomotive_query_start_time
    
    def are_locomotives_loaded(self):
        """Check if locomotives have been loaded"""
        return self.locomotives_loaded
    
    def set_locomotives_loaded(self, loaded):
        """Set locomotives loaded status"""
        self.locomotives_loaded = loaded
    
    def reset_query_state(self):
        """Reset locomotive query state"""
        self.locomotive_query_pending = False
        self.locomotive_query_start_time = 0
    
    def socket_listener(self):
        """Background thread for listening to socket data"""
        print("Socket listener started")
        
        while self.running:
            try:
                data = self.socket_client.recv(4096)
                if data:
                    if self.data_callback:
                        self.data_callback(data)
                else:
                    print("Connection closed by server")
                    self.rocrail_status = "lost"
                    break
            except:
                # Any socket error - continue with small delay
                time.sleep(0.01)
                continue
        
        print("Socket listener stopped")
    
    def start_connection(self, host, port, callback_function):
        """
        Start a socket connection and monitor it in background
        
        Args:
            host: Server hostname or IP
            port: Server port
            callback_function: Function to call when data is received
        """
        # Set connecting status
        self.rocrail_status = "connecting"
        
        try:
            # Create socket (simple MicroPython way)
            self.socket_client = socket.socket()
            print(f"Connecting to {host}:{port}...")
            self.socket_client.connect((host, port))
            
            # Set callback function
            self.data_callback = callback_function
            self.running = True
            
            # Connection successful
            self.rocrail_status = "connected"
            self.last_rocrail_activity_time = time.ticks_ms()
            self.last_rocrail_send_success = True
            
            # Start listener thread
            _thread.start_new_thread(self.socket_listener, ())
            
            print(f"Connected to server {host}:{port}")
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.rocrail_status = "lost"  # Could not connect
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
            return False
    
    def stop_connection(self):
        """Stop the socket connection and background thread"""
        if self.socket_client:
            self.running = False
            self.rocrail_status = "disconnected"
            time.sleep(0.2)  # Give time for the thread to exit
            self.socket_client.close()
            self.socket_client = None
            print("Socket connection closed")
    
    def handle_data(self, data):
        """Process received data from RocRail server"""
        # Update last activity time (data received)
        self.last_rocrail_activity_time = time.ticks_ms()
        
        # If we receive data, connection is definitely working - restore status if lost
        if self.rocrail_status == "lost":
            self.rocrail_status = "connected"
            print("RocRail connection restored - data received")
        elif self.rocrail_status != "connected":
            self.rocrail_status = "connected"
        
        # Simple decode without keyword arguments for MicroPython compatibility
        try:
            data_str = data.decode('utf-8')
        except:
            data_str = str(data)  # Fallback if decode fails
        
        # Debug: Print received data
        debug_print(f"Received data ({len(data_str)} chars): {data_str[:200]}...")
        
        # Accumulate XML data in buffer
        self.xml_buffer += data_str
        
        # Debug: Print current buffer state
        debug_print(f"XML buffer size: {len(self.xml_buffer)}, locomotives_loaded: {self.locomotives_loaded}")
        
        # Only process locomotive data if we haven't loaded locomotives yet
        if not self.locomotives_loaded:
            debug_print("Processing locomotive data...")
            
            # Check for locomotive list response
            if 'lclist' in self.xml_buffer.lower() or '<lc ' in self.xml_buffer:
                debug_print("Found lclist or <lc> in buffer, trying to parse...")
                if self.loco_list.update_from_rocrail_response(self.xml_buffer):
                    debug_print("Successfully parsed locomotive data from RocRail!")
                    # Call display update callback if provided
                    if self.display_update_callback:
                        debug_print("Calling display update callback...")
                        self.display_update_callback()
                    else:
                        debug_print("WARNING: No display update callback set!")
                    self.locomotive_query_pending = False
                    self.locomotive_query_start_time = 0
                    self.locomotives_loaded = True  # Stop further locomotive queries
                else:
                    debug_print("Failed to parse locomotive data from buffer")
            
            # Check for complete model response
            elif self.locomotive_query_pending and ('</model>' in self.xml_buffer or '</xmlh>' in self.xml_buffer):
                debug_print("Found complete model response, trying to parse...")
                if self.loco_list.update_from_rocrail_response(self.xml_buffer):
                    debug_print("Successfully parsed locomotive data from model response!")
                    # Call display update callback if provided
                    if self.display_update_callback:
                        debug_print("Calling display update callback...")
                        self.display_update_callback()
                    else:
                        debug_print("WARNING: No display update callback set!")
                    self.locomotives_loaded = True  # Stop further locomotive queries
                else:
                    debug_print("Failed to parse locomotive data from model response")
                self.locomotive_query_pending = False
                self.locomotive_query_start_time = 0
            else:
                debug_print("No locomotive data patterns found in buffer yet")
        else:
            debug_print("Locomotives already loaded, ignoring received data")
        
        # Prevent buffer from growing too large
        if len(self.xml_buffer) > 8192:  # 8KB limit
            self.xml_buffer = self.xml_buffer[-4096:]  # Keep only the last 4KB
            debug_print("XML buffer truncated to prevent memory issues")
    
    def send_speed_and_direction(self, speed, direction):
        """Send locomotive speed and direction via RocRail RCP XML format"""
        current_loco_id = self.loco_list.get_selected_id()
        if not current_loco_id:
            return False
        
        if self.socket_client:
            try:
                # Format the message according to RocRail protocol
                message = f'<lc id="{current_loco_id}" V="{speed}" dir="{direction}"/>'
                message_len = len(message)
                message_and_header = f'<xmlh><xml size="{message_len}"/></xmlh>{message}'
                self.socket_client.send(message_and_header.encode())
                
                # Track successful send
                self.last_rocrail_activity_time = time.ticks_ms()
                self.last_rocrail_send_success = True
                if self.rocrail_status != "connected":
                    self.rocrail_status = "connected"
                
                return True
            except Exception as e:
                print(f"Send error: {e}")
                self.last_rocrail_send_success = False
                self.rocrail_status = "lost"
                return False
        return False
    
    def send_light_command(self, light_on_off):
        """Send locomotive light command via RocRail RCP XML format"""
        current_loco_id = self.loco_list.get_selected_id()
        if not current_loco_id:
            return False
        
        if self.socket_client:
            try:
                message = f'<fn id="{current_loco_id}" fn0="{light_on_off}"/>'
                message_len = len(message)
                message_and_header = f'<xmlh><xml size="{message_len}"/></xmlh>{message}'
                self.socket_client.send(message_and_header.encode())
                
                # Track successful send
                self.last_rocrail_activity_time = time.ticks_ms()
                self.last_rocrail_send_success = True
                if self.rocrail_status != "connected":
                    self.rocrail_status = "connected"
                
                return True
            except Exception as e:
                print(f"Send error: {e}")
                self.last_rocrail_send_success = False
                self.rocrail_status = "lost"
                return False
        return False
    
    def query_locomotives(self):
        """Query all locomotives from RocRail server using specific locomotive list command"""
        debug_print(f"query_locomotives called - socket_client: {self.socket_client is not None}")
        
        if self.socket_client:
            try:
                # Send specific locomotive list command (as used in other programs)
                message = '<model cmd="lclist"/>'
                message_len = len(message)
                message_and_header = f'<xmlh><xml size="{message_len}" name="model"/></xmlh>{message}'
                
                debug_print(f"Sending locomotive query: {message_and_header}")
                self.socket_client.send(message_and_header.encode())
                
                # Track successful send
                self.last_rocrail_activity_time = time.ticks_ms()
                self.last_rocrail_send_success = True
                if self.rocrail_status != "connected":
                    self.rocrail_status = "connected"
                
                # Set flag to indicate we're expecting locomotive data
                self.locomotive_query_pending = True
                self.locomotive_query_start_time = time.ticks_ms()
                
                debug_print("Locomotive query sent successfully!")
                debug_print(f"Query pending: {self.locomotive_query_pending}, Start time: {self.locomotive_query_start_time}")
                
                return True
            except Exception as e:
                print(f"Query error: {e}")
                self.locomotive_query_pending = False
                self.locomotive_query_start_time = 0
                self.last_rocrail_send_success = False
                self.rocrail_status = "lost"
                return False
        else:
            debug_print("Cannot query locomotives - no socket connection")
        return False

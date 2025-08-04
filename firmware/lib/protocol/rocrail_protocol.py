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
            
            # Debug: Check what we have in buffer
            has_lclist_start = '<lclist>' in self.xml_buffer
            has_lclist_end = '</lclist>' in self.xml_buffer
            debug_print(f"Buffer analysis: has_start={has_lclist_start}, has_end={has_lclist_end}, buffer_size={len(self.xml_buffer)}")
            
            # Strategy 1: Try to parse complete lclist if we have both start and end
            if has_lclist_start and has_lclist_end:
                debug_print("Found complete lclist structure in buffer, trying to parse...")
                if self.loco_list.update_from_rocrail_response(self.xml_buffer):
                    debug_print("Successfully parsed locomotive data from complete lclist!")
                    # Call display update callback if provided
                    if self.display_update_callback:
                        debug_print("Calling display update callback...")
                        self.display_update_callback()
                    else:
                        debug_print("WARNING: No display update callback set!")
                    self.locomotive_query_pending = False
                    self.locomotive_query_start_time = 0
                    self.locomotives_loaded = True  # Stop further locomotive queries
                    # Clear buffer after successful parsing to free memory
                    self.xml_buffer = ""
                    debug_print("XML buffer cleared after successful locomotive parsing")
                    return  # Exit early after successful parsing
                else:
                    debug_print("Failed to parse locomotive data from complete lclist")
            
            # Strategy 2: Streaming extraction if we have locomotive data but incomplete structure
            elif has_lclist_start or ('lc ' in self.xml_buffer and 'id=' in self.xml_buffer):
                debug_print("Attempting streaming locomotive extraction from buffer...")
                locomotives_found = self.loco_list.extract_locomotives_streaming(self.xml_buffer)
                
                if locomotives_found:
                    debug_print(f"Streaming extraction found {len(locomotives_found)} locomotives")
                    # Add found locomotives to the list
                    added = 0
                    for loco_id in locomotives_found:
                        if self.loco_list.add_locomotive(loco_id):
                            added += 1
                            debug_print(f"Added locomotive via streaming: {loco_id}")
                    
                    if added > 0:
                        self.loco_list.save_to_file()
                        debug_print(f"Streaming: Successfully added {added} locomotives")
                        # Call display update callback
                        if self.display_update_callback:
                            debug_print("Calling display update callback after streaming parse...")
                            self.display_update_callback()
                        
                        # If we got locomotives via streaming, consider the job done
                        self.locomotive_query_pending = False
                        self.locomotive_query_start_time = 0
                        self.locomotives_loaded = True
                        self.xml_buffer = ""  # Clear buffer
                        debug_print("Locomotive loading completed via streaming extraction")
                        return
                else:
                    debug_print("Streaming extraction found no locomotives")
            
            # Strategy 3: Wait for more data
            if has_lclist_start and not has_lclist_end:
                debug_print("Found start of lclist but no end tag yet - waiting for more data")
            elif not has_lclist_start and has_lclist_end:
                debug_print("WARNING: Found end of lclist but no start tag - buffer may have been truncated incorrectly!")
            elif self.locomotive_query_pending and 'lc ' in self.xml_buffer:
                debug_print("Found locomotive data fragments - attempting streaming extraction next")
            else:
                debug_print("No locomotive data patterns found in buffer yet")
        else:
            debug_print("Locomotives already loaded, ignoring received data")
        
        # Prevent buffer from growing too large - but preserve lclist boundaries
        if len(self.xml_buffer) > 20480:  # 20KB limit (increased further)
            # If we're waiting for locomotive data, try to preserve important data
            if not self.locomotives_loaded and self.locomotive_query_pending:
                # Strategy 1: Try streaming extraction before truncating
                debug_print("Buffer getting large - attempting streaming extraction before truncation...")
                locomotives_found = self.loco_list.extract_locomotives_streaming(self.xml_buffer)
                
                if locomotives_found:
                    debug_print(f"Emergency streaming found {len(locomotives_found)} locomotives")
                    added = 0
                    for loco_id in locomotives_found:
                        if self.loco_list.add_locomotive(loco_id):
                            added += 1
                    
                    if added > 0:
                        self.loco_list.save_to_file()
                        debug_print(f"Emergency streaming: Successfully saved {added} locomotives")
                        if self.display_update_callback:
                            self.display_update_callback()
                        self.locomotive_query_pending = False
                        self.locomotive_query_start_time = 0
                        self.locomotives_loaded = True
                        self.xml_buffer = ""  # Clear all
                        debug_print("Locomotive loading completed via emergency streaming")
                        return
                
                # Strategy 2: Preserve lclist structure if possible
                lclist_start = self.xml_buffer.find('<lclist>')
                if lclist_start != -1:
                    # Keep from lclist start onwards, but limit to 8KB
                    preserved_data = self.xml_buffer[lclist_start:]
                    if len(preserved_data) > 8192:
                        preserved_data = preserved_data[:8192]
                    self.xml_buffer = preserved_data
                    debug_print("XML buffer truncated but preserved lclist start (8KB)")
                else:
                    # Keep last 4KB as fallback
                    self.xml_buffer = self.xml_buffer[-4096:]
                    debug_print("XML buffer truncated - kept last 4KB for safety")
            else:
                # Standard truncation for non-locomotive data
                self.xml_buffer = self.xml_buffer[-4096:]
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

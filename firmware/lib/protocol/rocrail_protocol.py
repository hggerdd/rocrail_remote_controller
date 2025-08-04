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
        
        receive_buffer_size = 4096  # Smaller buffer to prevent memory issues
        consecutive_errors = 0
        
        while self.running:
            try:
                data = self.socket_client.recv(receive_buffer_size)
                if data:
                    consecutive_errors = 0  # Reset error counter on successful receive
                    if self.data_callback:
                        self.data_callback(data)
                else:
                    print("Connection closed by server")
                    self.rocrail_status = "lost"
                    break
            except OSError as e:
                # Network-related errors
                consecutive_errors += 1
                if consecutive_errors > 10:
                    print(f"Socket listener: Too many consecutive errors ({consecutive_errors}), stopping")
                    self.rocrail_status = "lost"
                    break
                time.sleep(0.01)
                continue
            except Exception as e:
                # Other errors - log and continue
                consecutive_errors += 1
                if consecutive_errors <= 3:  # Only log first few errors to avoid spam
                    print(f"Socket listener error: {e}")
                if consecutive_errors > 20:
                    print(f"Socket listener: Critical error count ({consecutive_errors}), stopping")
                    self.rocrail_status = "lost"
                    break
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
        
        # Safety check: Reject abnormally large data packets to prevent memory issues
        if len(data_str) > 8192:  # More than 8KB in single packet is suspicious
            print(f"[MEMORY] WARNING: Rejecting large data packet ({len(data_str)} bytes) to prevent memory issues")
            return
        
        # Debug: Print received data (only if still loading)
        if not self.locomotives_loaded:
            debug_print(f"Received data ({len(data_str)} chars): {data_str[:200]}...")
        
        # Memory management: If locomotives are already loaded, we don't need to buffer status updates
        if self.locomotives_loaded:
            # Just process for connection monitoring, don't accumulate in buffer
            # Status updates like <lc id="BR103" V="68" dir="true"...> are not needed
            if len(self.xml_buffer) > 1024:  # Keep small buffer for connection monitoring
                self.xml_buffer = ""
            return
        
        # Accumulate XML data in buffer ONLY if still loading locomotives
        self.xml_buffer += data_str
        
        # Debug: Print current buffer state
        debug_print(f"XML buffer size: {len(self.xml_buffer)}, locomotives_loaded: {self.locomotives_loaded}")
        
        # Check memory usage and log warnings
        try:
            import gc
            gc.collect()
            free_mem = gc.mem_free()
            if free_mem < 20000:  # Less than 20KB free memory
                debug_print(f"⚠️  LOW MEMORY WARNING: {free_mem} bytes free")
        except:
            pass
        
        # Process locomotive data if we haven't loaded locomotives yet
        debug_print("Processing locomotive data...")
        
        # Check for complete locomotive list response - this is the main strategy
        if '<lclist>' in self.xml_buffer and '</lclist>' in self.xml_buffer:
            debug_print("Found complete lclist structure in buffer, attempting intelligent parsing...")
            if self.loco_list.update_from_rocrail_response(self.xml_buffer):
                debug_print("✅ Successfully parsed locomotive data from RocRail!")
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
                debug_print("✅ Locomotive loading completed successfully - buffer cleared")
                # Disable debug output to save memory
                global DEBUG_LOCOMOTIVE_LOADING
                DEBUG_LOCOMOTIVE_LOADING = False
                print("[MEMORY] Locomotive loading complete - disabled debug output to save memory")
                # Force garbage collection after locomotive loading
                try:
                    import gc
                    gc.collect()
                    print(f"[MEMORY] Memory after locomotive loading: {gc.mem_free()} bytes free")
                except:
                    pass
            else:
                debug_print("❌ Failed to parse locomotive data from complete lclist")
        
        # Check for partial locomotive data - wait for more
        elif '<lclist>' in self.xml_buffer and '</lclist>' not in self.xml_buffer:
            debug_print("📄 Found start of lclist but no end tag yet - waiting for more data")
        elif '<lclist>' not in self.xml_buffer and '</lclist>' in self.xml_buffer:
            debug_print("⚠️  Found end of lclist but no start tag - buffer was truncated, data may be lost")
        else:
            debug_print("🔍 No complete locomotive data found in buffer yet")
        
        # Aggressive buffer management during locomotive loading
        if len(self.xml_buffer) > 16384:  # 16KB limit (reduced from 24KB)
            # Find the start of lclist and preserve it
            lclist_start = self.xml_buffer.find('<lclist>')
            if lclist_start != -1:
                # Keep from lclist start onwards, but limit to 8KB
                preserved_data = self.xml_buffer[lclist_start:]
                if len(preserved_data) > 8192:
                    preserved_data = preserved_data[:8192]
                self.xml_buffer = preserved_data
                debug_print(f"XML buffer truncated but preserved lclist start ({len(preserved_data)} bytes)")
            else:
                # No lclist start found - keep last 4KB as safety net
                self.xml_buffer = self.xml_buffer[-4096:]
                debug_print("XML buffer truncated - kept last 4KB for safety")
            
            # Force garbage collection after buffer truncation
            try:
                import gc
                gc.collect()
                debug_print(f"Memory after buffer truncation: {gc.mem_free()} bytes free")
            except:
                pass
    
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

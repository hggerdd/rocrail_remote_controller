import socket
import time
import _thread

# Robust config import with fallbacks
try:
    from config import (RECONNECT_DELAY_FAST, RECONNECT_DELAY_SLOW, 
                       RECONNECT_FAST_ATTEMPTS, RECONNECT_UNLIMITED, SOCKET_TIMEOUT)
except ImportError as e:
    print(f"Config import error: {e}, using fallback values")
    RECONNECT_DELAY_FAST = 3000
    RECONNECT_DELAY_SLOW = 8000  
    RECONNECT_FAST_ATTEMPTS = 3
    RECONNECT_UNLIMITED = True
    SOCKET_TIMEOUT = 10

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
        self.rocrail_status = "disconnected"  # States: "disconnected", "connecting", "connected", "lost", "reconnecting"
        self.last_rocrail_activity_time = 0
        self.last_rocrail_send_success = True
        
        # Reconnection management
        self.reconnect_running = False
        self.reconnect_attempts = 0
        self.host = None
        self.port = None
        self._socket_lock = False  # Simple lock for MicroPython
        self.connection_established_time = 0  # Track when connection was first established
        self.reconnect_enabled = False  # Only enable after stable connection
        
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
    
    def _acquire_socket_lock(self):
        """Simple socket lock for MicroPython"""
        timeout = 50  # 500ms timeout
        while self._socket_lock and timeout > 0:
            time.sleep(0.01)
            timeout -= 1
        if timeout > 0:
            self._socket_lock = True
            return True
        return False
    
    def _release_socket_lock(self):
        """Release socket lock"""
        self._socket_lock = False
    
    def _cleanup_socket(self):
        """Clean up socket connection safely"""
        if not self._acquire_socket_lock():
            print("Could not acquire socket lock for cleanup")
            return
            
        try:
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass  # Ignore cleanup errors
                self.socket_client = None
                
            # Force garbage collection after socket cleanup
            try:
                import gc
                gc.collect()
            except:
                pass
                
            # Give system time to recover
            time.sleep(0.1)
                
        except Exception as e:
            print(f"Error during socket cleanup: {e}")
        finally:
            self._release_socket_lock()
    
    def _start_reconnect_thread(self):
        """Start automatic reconnection thread"""
        # Don't start reconnect during initial connection phase
        if not self.reconnect_enabled:
            print("Reconnect not enabled yet - skipping auto-reconnect")
            return
            
        # Prevent multiple reconnect threads
        if self.reconnect_running:
            print("Reconnect thread already running - skipping")
            return
            
        if not self.host or not self.port:
            print("No host/port configured for reconnect")
            return
            
        print("Starting reconnect thread...")
        self.reconnect_running = True
        self.reconnect_attempts = 0
        
        try:
            _thread.start_new_thread(self._reconnect_loop, ())
            print("Reconnect thread started successfully")
        except OSError as e:
            print(f"Failed to start reconnect thread: {e}")
            self.reconnect_running = False
    
    def _reconnect_loop(self):
        """Background reconnection loop"""
        print("Starting reconnection loop...")
        
        while self.reconnect_running and RECONNECT_UNLIMITED:
            try:
                # Determine delay based on attempt count
                if self.reconnect_attempts < RECONNECT_FAST_ATTEMPTS:
                    delay = RECONNECT_DELAY_FAST
                else:
                    delay = RECONNECT_DELAY_SLOW
                
                # Always wait before retry (even first attempt)
                print(f"Reconnect attempt {self.reconnect_attempts + 1} in {delay}ms...")
                time.sleep(delay / 1000.0)
                
                # Check if we should still continue
                if not self.reconnect_running:
                    print("Reconnect cancelled")
                    break
                
                # Update status to reconnecting
                self.rocrail_status = "reconnecting"
                self.reconnect_attempts += 1
                
                # Attempt reconnection
                print(f"Reconnecting to {self.host}:{self.port} (attempt {self.reconnect_attempts})...")
                
                # Clean up old connection with pause
                self._cleanup_socket()
                time.sleep(0.5)  # Give system time to recover
                
                # Try to establish new connection
                if self._attempt_connection():
                    print(f"Reconnection successful after {self.reconnect_attempts} attempts!")
                    # Reset and exit loop
                    self.reconnect_attempts = 0
                    
                    # Restart locomotive query after reconnection
                    if not self.locomotives_loaded:
                        print("Restarting locomotive query after reconnection...")
                        time.sleep(1.0)  # Longer delay before querying
                        self.query_locomotives()
                    
                    # Successfully connected - exit loop
                    break
                
                # Progressive backoff for stability
                if self.reconnect_attempts > 10:
                    print("Many attempts - adding extra pause for system recovery...")
                    time.sleep(5)  # Extra pause after many attempts
                
                # Limit attempts to prevent infinite loops
                if self.reconnect_attempts > 30:  # Reduced safety limit
                    print("Too many reconnect attempts, long pause...")
                    time.sleep(30)  # 30 second pause
                    self.reconnect_attempts = 5   # Reset to slower retry mode
                
            except Exception as e:
                print(f"Reconnection error: {e}")
                time.sleep(1)  # Pause on error
                
        print("Reconnection loop ended")
        self.reconnect_running = False
    
    def _attempt_connection(self):
        """Attempt to establish socket connection"""
        try:
            if not self._acquire_socket_lock():
                print("Could not acquire lock for connection attempt")
                return False
                
            # Create new socket WITHOUT timeout for normal operation
            self.socket_client = socket.socket()
            # Do NOT set timeout: self.socket_client.settimeout(SOCKET_TIMEOUT)
            
            # Connect to server
            print(f"Attempting connection to {self.host}:{self.port}...")
            self.socket_client.connect((self.host, self.port))
            
            # Connection successful
            self.rocrail_status = "connected"
            self.last_rocrail_activity_time = time.ticks_ms()
            self.last_rocrail_send_success = True
            self.running = True
            
            # Brief pause before starting listener
            time.sleep(0.2)
            
            # Start listener thread
            _thread.start_new_thread(self.socket_listener, ())
            
            print("Connection successful!")
            return True
            
        except Exception as e:
            print(f"Connection attempt failed: {e}")
            self.rocrail_status = "lost"
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
                
            return False
        finally:
            self._release_socket_lock()
    
    def socket_listener(self):
        """Background thread for listening to socket data"""
        print("Socket listener started")
        
        receive_buffer_size = 4096  # min 4096 required for robust work
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
                    # Only start reconnect if not already running
                    if not self.reconnect_running:
                        self._start_reconnect_thread()
                    break
            except OSError as e:
                # Network-related errors
                consecutive_errors += 1
                if consecutive_errors > 10:  # Back to original threshold
                    print(f"Socket listener: Too many consecutive errors ({consecutive_errors}), starting reconnect")
                    self.rocrail_status = "lost"
                    # Only start reconnect if not already running
                    if not self.reconnect_running:
                        self._start_reconnect_thread()
                    break
                time.sleep(0.01)  # Back to original timing
                continue
            except Exception as e:
                # Other errors - log and continue
                consecutive_errors += 1
                if consecutive_errors <= 3:  # Only log first few errors to avoid spam
                    print(f"Socket listener error: {e}")
                if consecutive_errors > 20:  # Back to original threshold
                    print(f"Socket listener: Critical error count ({consecutive_errors}), starting reconnect")
                    self.rocrail_status = "lost"
                    # Only start reconnect if not already running
                    if not self.reconnect_running:
                        self._start_reconnect_thread()
                    break
                time.sleep(0.01)  # Back to original timing
                continue
        
        print("Socket listener stopped")
        self.running = False
    
    def start_connection(self, host, port, callback_function):
        """
        Start a socket connection and monitor it in background
        
        Args:
            host: Server hostname or IP
            port: Server port
            callback_function: Function to call when data is received
        """
        # Store connection parameters for reconnection
        self.host = host
        self.port = port
        self.data_callback = callback_function
        
        # Set connecting status
        self.rocrail_status = "connecting"
        
        try:
            # Create socket (simple MicroPython way - like original)
            self.socket_client = socket.socket()
            print(f"Connecting to {host}:{port}...")
            self.socket_client.connect((host, port))
            
            # Connection successful
            self.rocrail_status = "connected"
            self.last_rocrail_activity_time = time.ticks_ms()
            self.last_rocrail_send_success = True
            self.running = True
            self.connection_established_time = time.ticks_ms()
            
            # Start listener thread
            _thread.start_new_thread(self.socket_listener, ())
            
            print(f"Connected to server {host}:{port}")
            return True
            
        except Exception as e:
            print(f"Connection error: {e}")
            self.rocrail_status = "lost"
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
            # NO auto-reconnect on initial connection failure
            print("Initial connection failed - no auto-reconnect during startup")
            return False
    
    def stop_connection(self):
        """Stop the socket connection and background thread"""
        print("Stopping connection and reconnect threads...")
        
        # Stop reconnection attempts
        self.reconnect_running = False
        
        # Stop socket operations
        self.running = False
        self.rocrail_status = "disconnected"
        
        # Clean up socket
        self._cleanup_socket()
        
        # Give threads time to exit
        time.sleep(0.3)
        
        print("Socket connection and reconnect threads stopped")
    
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
                
                # Enable reconnect after successful locomotive loading
                self.reconnect_enabled = True
                print("System stable - reconnect logic enabled")
                
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
                # Only start reconnect if not already running
                if not self.reconnect_running:
                    self._start_reconnect_thread()
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
                # Only start reconnect if not already running
                if not self.reconnect_running:
                    self._start_reconnect_thread()
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
                # Only start reconnect if not already running
                if not self.reconnect_running:
                    self._start_reconnect_thread()
                return False
        else:
            debug_print("Cannot query locomotives - no socket connection")
        return False

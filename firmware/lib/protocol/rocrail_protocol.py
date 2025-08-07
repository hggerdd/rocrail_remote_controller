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
            print("Socket lock fail")
            return
            
        try:
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
                
            try:
                import gc
                gc.collect()
            except:
                pass
                
            time.sleep(0.1)
                
        except Exception as e:
            print(f"Socket cleanup err: {e}")
        finally:
            self._release_socket_lock()
    
    def _start_reconnect_thread(self):
        """Start automatic reconnection thread"""
        if not self.reconnect_enabled:
            print("Recon not enabled")
            return
            
        if self.reconnect_running:
            print("Recon already run")
            return
            
        if not self.host or not self.port:
            print("No host/port")
            return
            
        print("Start recon thread...")
        self.reconnect_running = True
        self.reconnect_attempts = 0
        
        try:
            _thread.start_new_thread(self._reconnect_loop, ())
            print("Recon thread OK")
        except OSError as e:
            print(f"Recon thread fail: {e}")
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
                
                print(f"Recon #{self.reconnect_attempts + 1} in {delay}ms...")
                time.sleep(delay / 1000.0)
                
                if not self.reconnect_running:
                    print("Recon cancel")
                    break
                
                self.rocrail_status = "reconnecting"
                self.reconnect_attempts += 1
                
                print(f"RR recon→{self.host}:{self.port} (#{self.reconnect_attempts})")
                
                self._cleanup_socket()
                time.sleep(0.5)
                
                if self._attempt_connection():
                    print(f"Recon OK after {self.reconnect_attempts} tries!")
                    self.reconnect_attempts = 0
                    
                # Restart locomotive query after reconnection
                if not self.locomotives_loaded:
                    print("Requery locos after recon...")
                    time.sleep(1.0)
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
                print("Lock fail")
                return False
                
            self.socket_client = socket.socket()
            print(f"Try→{self.host}:{self.port}")
            self.socket_client.connect((self.host, self.port))
            
            self.rocrail_status = "connected"
            self.last_rocrail_activity_time = time.ticks_ms()
            self.last_rocrail_send_success = True
            self.running = True
            
            time.sleep(0.2)
            
            _thread.start_new_thread(self.socket_listener, ())
            
            print("Conn✓")
            return True
            
        except Exception as e:
            print(f"Conn fail: {e}")
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
        print("Socket listener OK")
        
        receive_buffer_size = 4096
        consecutive_errors = 0
        
        while self.running:
            try:
                data = self.socket_client.recv(receive_buffer_size)
                if data:
                    consecutive_errors = 0
                    if self.data_callback:
                        self.data_callback(data)
                else:
                    print("Server closed conn")
                    self.rocrail_status = "lost"
                    if not self.reconnect_running:
                        self._start_reconnect_thread()
                    break
            except OSError as e:
                consecutive_errors += 1
                if consecutive_errors > 10:
                    print(f"Socket err#{consecutive_errors}→recon")
                    self.rocrail_status = "lost"
                    if not self.reconnect_running:
                        self._start_reconnect_thread()
                    break
                time.sleep(0.01)
                continue
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors <= 3:
                    print(f"Socket ex: {e}")
                if consecutive_errors > 20:
                    print(f"Critical err#{consecutive_errors}→recon")
                    self.rocrail_status = "lost"
                    if not self.reconnect_running:
                        self._start_reconnect_thread()
                    break
                time.sleep(0.01)
                continue
        
        print("Socket listener stop")
        self.running = False
    
    def start_connection(self, host, port, callback_function):
        """
        Start a socket connection and monitor it in background
        """
        self.host = host
        self.port = port
        self.data_callback = callback_function
        self.rocrail_status = "connecting"
        
        try:
            self.socket_client = socket.socket()
            print(f"RR conn→{host}:{port}")
            self.socket_client.connect((host, port))
            
            self.rocrail_status = "connected"
            self.last_rocrail_activity_time = time.ticks_ms()
            self.last_rocrail_send_success = True
            self.running = True
            self.connection_established_time = time.ticks_ms()
            
            _thread.start_new_thread(self.socket_listener, ())
            
            print(f"RR conn OK")
            return True
            
        except Exception as e:
            print(f"RR conn err: {e}")
            self.rocrail_status = "lost"
            if self.socket_client:
                try:
                    self.socket_client.close()
                except:
                    pass
                self.socket_client = None
            print("Init conn fail→no auto-recon")
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
        self.last_rocrail_activity_time = time.ticks_ms()
        
        if self.rocrail_status == "lost":
            self.rocrail_status = "connected"
            print("RR conn restored")
        elif self.rocrail_status != "connected":
            self.rocrail_status = "connected"
        
        try:
            data_str = data.decode('utf-8')
        except:
            data_str = str(data)
        
        if len(data_str) > 8192:
            print(f"[MEM] Large pkt rejected: {len(data_str)}B")
            return
        
        if not self.locomotives_loaded:
            debug_print(f"RX {len(data_str)}B")
        
        if self.locomotives_loaded:
            if len(self.xml_buffer) > 1024:
                self.xml_buffer = ""
            return
        
        self.xml_buffer += data_str
        
        debug_print(f"Buf: {len(self.xml_buffer)}B")
        
        try:
            import gc
            gc.collect()
            free_mem = gc.mem_free()
            if free_mem < 20000:
                debug_print(f"⚠️ MEM: {free_mem}B")
        except:
            pass
        
        debug_print("Parse locos...")
        
        if '<lclist>' in self.xml_buffer and '</lclist>' in self.xml_buffer:
            debug_print("Found lclist→parse")
            if self.loco_list.update_from_rocrail_response(self.xml_buffer):
                debug_print("✅ Locos parsed!")
                if self.display_update_callback:
                    debug_print("Update display...")
                    self.display_update_callback()
                else:
                    debug_print("No display callback!")
                self.locomotive_query_pending = False
                self.locomotive_query_start_time = 0
                self.locomotives_loaded = True
                
                self.reconnect_enabled = True
                print("System stable→recon enabled")
                
                self.xml_buffer = ""
                debug_print("✅ Locos loaded")
                global DEBUG_LOCOMOTIVE_LOADING
                DEBUG_LOCOMOTIVE_LOADING = False
                print("[MEM] Debug off")
                try:
                    import gc
                    gc.collect()
                    print(f"[MEM] {gc.mem_free()}B free")
                except:
                    pass
            else:
                debug_print("❌ Parse fail")
        
        elif '<lclist>' in self.xml_buffer and '</lclist>' not in self.xml_buffer:
            debug_print("📄 Partial lclist...")
        elif '<lclist>' not in self.xml_buffer and '</lclist>' in self.xml_buffer:
            debug_print("⚠️ Truncated lclist")
        else:
            debug_print("🔍 No lclist yet")
        
        if len(self.xml_buffer) > 16384:
            lclist_start = self.xml_buffer.find('<lclist>')
            if lclist_start != -1:
                preserved_data = self.xml_buffer[lclist_start:]
                if len(preserved_data) > 8192:
                    preserved_data = preserved_data[:8192]
                self.xml_buffer = preserved_data
                debug_print(f"Buf truncate, kept {len(preserved_data)}B")
            else:
                self.xml_buffer = self.xml_buffer[-4096:]
                debug_print("Buf truncate→4KB")
            
            try:
                import gc
                gc.collect()
                debug_print(f"MEM after trunc: {gc.mem_free()}B")
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
                print(f"Sending light command: {light_on_off} for loco ID {current_loco_id}")
                # message = f'<fn id="{current_loco_id}" fn=0 on="{light_on_off}"/>'
                message = f'<fn id="{current_loco_id}" f0="{light_on_off}" fnchanged="0"/>'
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

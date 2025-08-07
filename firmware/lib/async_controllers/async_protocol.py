"""
Async RocRail Protocol Handler
Replaces thread-based socket communication with asyncio
"""

import asyncio
import json
from config import *


class AsyncRocrailProtocol:
    """
    Async RocRail protocol communication
    Replaces thread-based socket handling with asyncio
    """
    
    def __init__(self, loco_list, state_manager):
        self.loco_list = loco_list
        self.state = state_manager
        
        # Connection management
        self.reader = None
        self.writer = None
        self.host = None
        self.port = None
        
        # Protocol state
        self.locomotives_loaded = False
        self.query_pending = False
        self.xml_buffer = ""
        
        # Async synchronization
        self._protocol_lock = asyncio.Lock()
        self._send_queue = []  # Simple list for MicroPython compatibility
        self._queue_event = asyncio.Event()  # Signal when queue has items
        
        # Connection monitoring
        self.last_activity_time = 0
        self.reconnect_task = None
        
    async def connect(self, host, port, timeout=10):
        """Connect to RocRail server"""
        self.host = host
        self.port = port
        
        await self.state.set_rocrail_status("connecting")
        
        async with self._protocol_lock:
            try:
                print(f"Connecting to RocRail: {host}:{port}")
                
                # Create connection with timeout - MicroPython compatible
                if hasattr(asyncio, 'wait_for'):
                    # Standard asyncio with timeout
                    self.reader, self.writer = await asyncio.wait_for(
                        asyncio.open_connection(host, port),
                        timeout=timeout
                    )
                else:
                    # Fallback for MicroPython without wait_for
                    self.reader, self.writer = await asyncio.open_connection(host, port)
                
                print("✓ RocRail connected")
                await self.state.set_rocrail_status("connected")
                
                # Start background tasks
                asyncio.create_task(self._receive_task())
                asyncio.create_task(self._send_task())
                
                return True
                
            except asyncio.TimeoutError:
                print("RocRail connection timeout")
                await self.state.set_rocrail_status("failed")
                return False
            except Exception as e:
                print(f"RocRail connection error: {e}")
                await self.state.set_rocrail_status("failed")
                return False
                
    async def disconnect(self):
        """Disconnect from RocRail server"""
        async with self._protocol_lock:
            try:
                if self.writer:
                    self.writer.close()
                    # MicroPython compatible - wait_closed may not exist
                    if hasattr(self.writer, 'wait_closed'):
                        try:
                            await self.writer.wait_closed()
                        except:
                            pass  # Ignore errors in wait_closed
                    
                self.reader = None
                self.writer = None
                
                print("RocRail disconnected")
                await self.state.set_rocrail_status("disconnected")
                
            except Exception as e:
                print(f"RocRail disconnect error: {e}")
                
    async def is_connected(self):
        """Check if connected to RocRail"""
        async with self._protocol_lock:
            # MicroPython compatible connection check
            return (self.writer is not None and 
                   self.reader is not None and
                   hasattr(self.writer, 'write'))
            
            
    async def _auto_reconnect(self):
        """Automatic reconnection with exponential backoff"""
        retry_delays = [1, 2, 5, 10, 30]  # Seconds between attempts
        attempt = 0
        
        while True:
            if await self.is_connected():
                print("Already connected, stopping auto-reconnect")
                break
                
            delay = retry_delays[min(attempt, len(retry_delays)-1)]
            print(f"Auto-reconnect in {delay}s (attempt {attempt+1})")
            await self.state.set_rocrail_status("reconnecting")
            
            await asyncio.sleep(delay)
            
            try:
                # Clean up old connection first
                await self.disconnect()
                await asyncio.sleep(0.5)
                
                # Try to reconnect
                if await self.connect(self.host, self.port):
                    print("✓ Auto-reconnect successful")
                    
                    # Re-query locomotives if needed
                    if not self.locomotives_loaded:
                        await asyncio.sleep(1)
                        await self.query_locomotives()
                    
                    break  # Success, exit loop
                else:
                    print(f"Auto-reconnect attempt {attempt+1} failed")
                    attempt += 1
                    
            except Exception as e:
                print(f"Auto-reconnect error: {e}")
                attempt += 1
                
        print("Auto-reconnect task ended")
            
    async def reconnect(self, max_attempts=5):
        """Attempt to reconnect to RocRail"""
        if not self.host or not self.port:
            return False
            
        for attempt in range(max_attempts):
            print(f"RocRail reconnection attempt {attempt + 1}/{max_attempts}")
            
            # Clean up old connection
            await self.disconnect()
            await asyncio.sleep(1)
            
            # Try to reconnect
            if await self.connect(self.host, self.port):
                # Re-query locomotives after reconnection
                if not self.locomotives_loaded:
                    await asyncio.sleep(1)
                    await self.query_locomotives()
                return True
                
            await asyncio.sleep(2)  # Wait between attempts
            
        return False
        
    async def _receive_task(self):
        """Background task for receiving data"""
        print("RocRail receive task started")
        
        try:
            while True:
                if not self.reader:
                    await asyncio.sleep(1)
                    continue
                    
                try:
                    # Read data from socket with timeout
                    data = await self.reader.read(4096)
                    if not data:
                        print("RocRail server closed connection")
                        await self.state.set_rocrail_status("lost")
                        await self.disconnect()
                        # Trigger reconnection
                        if not self.reconnect_task or self.reconnect_task.done():
                            self.reconnect_task = asyncio.create_task(self._auto_reconnect())
                        break
                        
                    # Process received data
                    await self._handle_received_data(data)
                    
                except OSError as e:
                    # Handle socket errors
                    if "[Errno 128]" in str(e) or "ENOTCONN" in str(e):
                        print(f"Receive connection lost: {e}")
                        await self.state.set_rocrail_status("lost")
                        await self.disconnect()
                        # Trigger reconnection
                        if not self.reconnect_task or self.reconnect_task.done():
                            self.reconnect_task = asyncio.create_task(self._auto_reconnect())
                        break
                    else:
                        print(f"Receive error: {e}")
                        await asyncio.sleep(0.5)
                        
        except Exception as e:
            print(f"Receive task error: {e}")
            await self.state.set_rocrail_status("lost")
        finally:
            print("RocRail receive task ended")
            
    async def _send_task(self):
        """Background task for sending queued messages"""
        print("RocRail send task started")
        
        try:
            while True:
                # Wait for message to be available in queue
                await self._queue_event.wait()
                
                # Process all queued messages
                while True:
                    async with self._protocol_lock:
                        if not self._send_queue:
                            self._queue_event.clear()
                            break
                        message = self._send_queue.pop(0)
                    
                    if not self.writer or not hasattr(self.writer, 'write'):
                        print("Cannot send - no connection")
                        await self.state.set_rocrail_status("lost")
                        # Trigger reconnection
                        if not self.reconnect_task or self.reconnect_task.done():
                            self.reconnect_task = asyncio.create_task(self._auto_reconnect())
                        continue
                        
                    try:
                        # Send message
                        self.writer.write(message)
                        await self.writer.drain()
                        
                        # Update activity time
                        import time
                        self.last_activity_time = time.ticks_ms()
                        
                        # Ensure connection status is correct
                        if await self.state.get_rocrail_status() != "connected":
                            await self.state.set_rocrail_status("connected")
                            
                    except OSError as e:
                        # Handle specific socket errors
                        if "[Errno 128]" in str(e) or "ENOTCONN" in str(e):
                            print(f"Connection lost: {e}")
                            await self.state.set_rocrail_status("lost")
                            # Close the broken connection
                            await self.disconnect()
                            # Trigger immediate reconnection
                            if not self.reconnect_task or self.reconnect_task.done():
                                self.reconnect_task = asyncio.create_task(self._auto_reconnect())
                        else:
                            print(f"Send error: {e}")
                            await self.state.set_rocrail_status("error")
                    except Exception as e:
                        print(f"Send error: {e}")
                        await self.state.set_rocrail_status("lost")
                
        except Exception as e:
            print(f"Send task error: {e}")
        finally:
            print("RocRail send task ended")
            
    async def _handle_received_data(self, data):
        """Process received data from RocRail"""
        try:
            data_str = data.decode('utf-8')
        except:
            data_str = str(data)
            
        # Update activity time
        import time
        self.last_activity_time = time.ticks_ms()
        
        # Update connection status if needed
        if await self.state.get_rocrail_status() != "connected":
            await self.state.set_rocrail_status("connected")
            
        # Handle locomotive list loading
        if not self.locomotives_loaded:
            await self._process_locomotive_data(data_str)
            
    async def _process_locomotive_data(self, data_str):
        """Process locomotive list data"""
        # Add to buffer
        self.xml_buffer += data_str
        
        # Check for complete locomotive list
        if '<lclist>' in self.xml_buffer and '</lclist>' in self.xml_buffer:
            print("Processing locomotive list...")
            
            try:
                # Parse locomotive list
                if self.loco_list.update_from_rocrail_response(self.xml_buffer):
                    print("✓ Locomotives loaded from RocRail")
                    self.locomotives_loaded = True
                    self.query_pending = False
                    
                    # Clear buffer to save memory
                    self.xml_buffer = ""
                    
                    # Run garbage collection
                    import gc
                    gc.collect()
                    
                else:
                    print("Failed to parse locomotive list")
                    
            except Exception as e:
                print(f"Locomotive parsing error: {e}")
                
        # Prevent buffer from growing too large
        elif len(self.xml_buffer) > 16384:
            # Try to preserve locomotive list data
            lclist_start = self.xml_buffer.find('<lclist>')
            if lclist_start != -1:
                self.xml_buffer = self.xml_buffer[lclist_start:]
            else:
                self.xml_buffer = self.xml_buffer[-4096:]  # Keep last 4KB
                
    async def _send_message(self, message):
        """Queue message for sending"""
        try:
            # Create XML message with header
            message_len = len(message)
            full_message = f'<xmlh><xml size="{message_len}"/></xmlh>{message}'
            
            # Queue for sending using list and event
            async with self._protocol_lock:
                self._send_queue.append(full_message.encode())
                self._queue_event.set()
            
            return True
            
        except Exception as e:
            print(f"Message queue error: {e}")
            return False
            
    async def send_speed_direction(self, speed, direction):
        """Send locomotive speed and direction command"""
        current_loco_id = self.loco_list.get_selected_id()
        if not current_loco_id:
            return False
            
        message = f'<lc id="{current_loco_id}" V="{speed}" dir="{direction}"/>'
        return await self._send_message(message)
        
    async def send_light_command(self, light_on_off):
        """Send locomotive light command"""
        current_loco_id = self.loco_list.get_selected_id()
        if not current_loco_id:
            return False
            
        message = f'<fn id="{current_loco_id}" f0="{light_on_off}" fnchanged="0"/>'
        return await self._send_message(message)
        
    async def query_locomotives(self):
        """Query all locomotives from RocRail server"""
        print("Querying locomotives...")
        
        self.query_pending = True
        message = '<model cmd="lclist"/>'
        
        # Send query with special header
        try:
            message_len = len(message)
            full_message = f'<xmlh><xml size="{message_len}" name="model"/></xmlh>{message}'
            
            # Queue for sending using list and event
            async with self._protocol_lock:
                self._send_queue.append(full_message.encode())
                self._queue_event.set()
            
            print("Locomotive query sent")
            return True
            
        except Exception as e:
            print(f"Query error: {e}")
            self.query_pending = False
            return False
            
    async def get_connection_info(self):
        """Get connection information"""
        async with self._protocol_lock:
            return {
                'connected': (self.writer is not None and 
                             self.reader is not None and
                             hasattr(self.writer, 'write')),
                'host': self.host,
                'port': self.port,
                'locomotives_loaded': self.locomotives_loaded,
                'last_activity': self.last_activity_time
            }

"""
ESP32 Locomotive Controller - AsyncIO Implementation
Refactored from polling-based to event-driven async architecture
"""

import asyncio
import network
import time
import machine
from machine import Pin

from config import *
from hardware_config import *
from lib.async_controllers.async_hardware import AsyncHardwareManager
from lib.async_controllers.async_wifi import AsyncWiFiManager  
from lib.async_controllers.async_protocol import AsyncRocrailProtocol
from lib.async_controllers.async_state import AsyncControllerState
from lib.async_controllers.async_leds import AsyncNeoPixelController
from lib.loco_list import LocoList

class LocomotiveControllerAsync:
    """Main asyncio-based locomotive controller"""
    
    def __init__(self):
        # Initialize core components
        self.loco_list = LocoList(LOCO_LIST_FILE)
        self.state = AsyncControllerState()
        
        # Initialize hardware managers
        self.hardware = AsyncHardwareManager()
        self.leds = AsyncNeoPixelController()
        self.wifi = AsyncWiFiManager(self.state)
        self.protocol = AsyncRocrailProtocol(self.loco_list, self.state)
        
        # Current locomotive state
        self.current_speed = 0
        self.current_direction = "true" 
        self.current_light = "false"
        
        # Task handles for cleanup
        self.tasks = []
        
        # System ready flag
        self.system_ready = asyncio.Event()
        
    async def initialize(self):
        """Initialize all subsystems"""
        print("Initializing asyncio controller...")
        
        # Initialize hardware
        await self.hardware.initialize()
        await self.leds.initialize()
        
        # Connect WiFi
        if await self.wifi.connect():
            await self.state.set_wifi_status("connected")
        else:
            await self.state.set_wifi_status("failed")
            return False
            
        # Connect to RocRail
        if await self.protocol.connect(ROCRAIL_HOST, ROCRAIL_PORT):
            await self.state.set_rocrail_status("connected")
        else:
            await self.state.set_rocrail_status("failed")
            return False
            
        # Initialize locomotive list
        await self._initialize_locomotives()
        
        # System is ready
        self.system_ready.set()
        print("✓ Asyncio controller ready!")
        return True
        
    async def _initialize_locomotives(self):
        """Initialize locomotive list"""
        if self.loco_list.get_count() == 0:
            self.loco_list.add_locomotive(DEFAULT_LOCO_ID)
            self.loco_list.save_to_file()
            
        # Query locomotives from RocRail
        await self.protocol.query_locomotives()
        
    async def start_tasks(self):
        """Start all async tasks"""
        print("Starting async tasks...")
        
        # Core system tasks
        self.tasks.extend([
            asyncio.create_task(self._hardware_input_task()),
            asyncio.create_task(self._speed_control_task()),
            asyncio.create_task(self._led_update_task()),
            asyncio.create_task(self._wifi_monitor_task()),
            asyncio.create_task(self._protocol_monitor_task()),
            asyncio.create_task(self._memory_monitor_task()),
            asyncio.create_task(self._heartbeat_task())
        ])
        
        print(f"Started {len(self.tasks)} async tasks")
        
    async def _hardware_input_task(self):
        """Handle hardware input processing"""
        print("Hardware input task started")
        
        while True:
            try:
                # Wait for system to be ready
                await self.system_ready.wait()
                
                # Process hardware inputs
                inputs = await self.hardware.read_all_inputs()
                
                # Handle locomotive selection
                if inputs['btn_up']:
                    if self.loco_list.select_next():
                        await self.state.signal_locomotive_changed()
                        await self.protocol.send_speed_direction(0, self.current_direction)
                        print(f"Loco: {self.loco_list.get_selected_id()}")
                        
                if inputs['btn_down']:
                    if self.loco_list.select_previous():
                        await self.state.signal_locomotive_changed()
                        await self.protocol.send_speed_direction(0, self.current_direction)
                        print(f"Loco: {self.loco_list.get_selected_id()}")
                
                # Handle direction button
                if inputs['direction']:
                    self.current_direction = "true" if self.current_direction == "false" else "false"
                    await self.state.signal_direction_changed()
                    await self.protocol.send_speed_direction(0, self.current_direction)
                    print(f"Direction: {self.current_direction[0]}")
                    
                # Handle emergency button
                if inputs['emergency']:
                    await self.state.signal_emergency_stop()
                    await self.protocol.send_speed_direction(0, self.current_direction)
                    print("⚠STOP!")
                    
                # Handle light button
                if inputs['light']:
                    self.current_light = "true" if self.current_light == "false" else "false"
                    await self.protocol.send_light_command(self.current_light)
                    print(f"Light: {self.current_light[0]}")
                    
                # Handle sound button
                if inputs['sound']:
                    print("🔊Horn")
                    
                # Update current speed from potentiometer
                self.current_speed = inputs['speed']
                
            except Exception as e:
                print(f"Hardware input error: {e}")
                await asyncio.sleep(0.1)
                
            await asyncio.sleep(BUTTON_CHECK_INTERVAL / 1000.0)
            
    async def _speed_control_task(self):
        """Handle speed control and sending"""
        print("Speed control task started")
        last_speed = -1
        
        while True:
            try:
                # Wait for system to be ready
                await self.system_ready.wait()
                
                # Check if speed sending is enabled
                if await self.state.is_speed_enabled():
                    if self.current_speed != last_speed:
                        await self.protocol.send_speed_direction(self.current_speed, self.current_direction)
                        last_speed = self.current_speed
                        print(f"Speed: {self.current_speed}")
                else:
                    # Check if we can re-enable speed (poti at zero)
                    if self.current_speed == 0:
                        await self.state.enable_speed_sending()
                        print("Speed enabled (poti=0)")
                        
            except Exception as e:
                print(f"Speed control error: {e}")
                await asyncio.sleep(0.1)
                
            await asyncio.sleep(SPEED_UPDATE_INTERVAL / 1000.0)
            
    async def _led_update_task(self):
        """Handle LED status updates"""
        print("LED update task started")
        
        while True:
            try:
                # Update all LED states
                wifi_status = await self.state.get_wifi_status()
                rocrail_status = await self.state.get_rocrail_status()
                speed_enabled = await self.state.is_speed_enabled()
                selected_loco = self.loco_list.get_selected_index()
                total_locos = self.loco_list.get_count()
                
                # Update LEDs
                await self.leds.update_wifi_status(wifi_status)
                await self.leds.update_rocrail_status(rocrail_status)
                await self.leds.update_direction(self.current_direction == "true")
                await self.leds.update_speed_warning(not speed_enabled)
                await self.leds.update_locomotive_selection(selected_loco, total_locos)
                
            except Exception as e:
                print(f"LED update error: {e}")
                await asyncio.sleep(0.1)
                
            await asyncio.sleep(NEOPIXEL_BLINK_INTERVAL / 1000.0)
            
    async def _wifi_monitor_task(self):
        """Monitor WiFi connection"""
        print("WiFi monitor task started")
        
        while True:
            try:
                if not await self.wifi.is_connected():
                    await self.state.set_wifi_status("connecting")
                    print("WiFi lost - reconnecting...")
                    
                    if await self.wifi.reconnect():
                        await self.state.set_wifi_status("connected")
                        print("WiFi reconnected")
                    else:
                        await self.state.set_wifi_status("failed")
                        print("WiFi reconnection failed")
                else:
                    if await self.state.get_wifi_status() != "connected":
                        await self.state.set_wifi_status("connected")
                        
            except Exception as e:
                print(f"WiFi monitor error: {e}")
                await asyncio.sleep(1)
                
            await asyncio.sleep(WIFI_CHECK_INTERVAL / 1000.0)
            
    async def _protocol_monitor_task(self):
        """Monitor RocRail protocol connection"""
        print("Protocol monitor task started")
        
        while True:
            try:
                # Check connection status less frequently as auto-reconnect handles recovery
                if not await self.protocol.is_connected():
                    rocrail_status = await self.state.get_rocrail_status()
                    
                    # Only intervene if not already reconnecting
                    if rocrail_status not in ["reconnecting", "connecting"]:
                        print("RocRail connection check failed - triggering reconnect")
                        await self.state.set_rocrail_status("reconnecting")
                        
                        # Trigger reconnection if not already running
                        if not self.protocol.reconnect_task or self.protocol.reconnect_task.done():
                            self.protocol.reconnect_task = asyncio.create_task(self.protocol._auto_reconnect())
                else:
                    # Connection is good, ensure status is correct
                    if await self.state.get_rocrail_status() not in ["connected", "connecting"]:
                        await self.state.set_rocrail_status("connected")
                        
            except Exception as e:
                print(f"Protocol monitor error: {e}")
                await asyncio.sleep(1)
                
            await asyncio.sleep(10.0)  # Check every 10 seconds (less frequent as auto-reconnect handles most cases)
            
    async def _memory_monitor_task(self):
        """Monitor memory usage"""
        print("Memory monitor task started")
        
        while True:
            try:
                import gc
                gc.collect()
                free_mem = gc.mem_free()
                
                if free_mem < 15000:
                    print(f"[MEM] Warning: {free_mem}B")
                    gc.collect()
                    gc.collect()
                    
            except Exception as e:
                print(f"Memory monitor error: {e}")
                
            await asyncio.sleep(60)  # Check every 60 seconds
            
    async def _heartbeat_task(self):
        """System heartbeat"""
        print("Heartbeat task started")
        
        while True:
            try:
                wifi_status = await self.state.get_wifi_status() 
                rocrail_status = await self.state.get_rocrail_status()
                print(f"[♥] W:{wifi_status[0]} R:{rocrail_status[0]} V:{self.current_speed}")
                
            except Exception as e:
                print(f"Heartbeat error: {e}")
                
            await asyncio.sleep(30)  # Every 30 seconds
            
    async def run(self):
        """Main run method"""
        try:
            # Initialize system
            if not await self.initialize():
                print("Initialization failed")
                return
                
            # Start all tasks
            await self.start_tasks()
            
            # Run main event loop - wait for all tasks
            print("Starting main event loop...")
            
            # MicroPython compatible - wait for tasks individually
            while self.tasks:
                try:
                    # Wait for any task to complete (shouldn't happen in normal operation)
                    await asyncio.sleep(1)
                    
                    # Check if any tasks have failed
                    failed_tasks = []
                    for task in self.tasks:
                        if task.done():
                            failed_tasks.append(task)
                    
                    if failed_tasks:
                        print(f"Tasks completed/failed: {len(failed_tasks)}")
                        for task in failed_tasks:
                            self.tasks.remove(task)
                            if task.exception():
                                print(f"Task error: {task.exception()}")
                                
                except Exception as e:
                    print(f"Event loop error: {e}")
                    break
            
        except KeyboardInterrupt:
            print("Program interrupted")
        except Exception as e:
            print(f"Main loop error: {e}")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up resources"""
        print("Cleaning up...")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        # Cleanup components
        await self.protocol.disconnect()
        await self.wifi.disconnect()
        await self.leds.cleanup()
        
        print("Cleanup complete")

# Main entry point
async def main():
    """Main async entry point"""
    controller = LocomotiveControllerAsync()
    await controller.run()

# Run the async controller - MicroPython compatible
def run_controller():
    """Run the controller with MicroPython compatible asyncio"""
    try:
        # Try asyncio.run() first (newer MicroPython)
        if hasattr(asyncio, 'run'):
            asyncio.run(main())
        else:
            # Fall back to event loop method (older MicroPython)
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
    except Exception as e:
        print(f"Error running controller: {e}")

if __name__ == "__main__":
    run_controller()

# controllers/loco_controller.py
import gc
import re
import rocrail

class LocoController:
    """Controller for locomotive via RocRail"""
    
    def __init__(self, rocrail, loco_id="BR103"):
        """Initialize locomotive controller
        
        Args:
            rocrail: RocrailProtocol instance
            loco_id: ID of the locomotive to control
        """
        self.rocrail = rocrail
        self.loco_id = loco_id
        self.current_speed = 0
        self.current_direction = True  # True = forward
        self.last_update_time = 0
        
        # Locomotive function states
        self.light_on = False
        self.sound_on = False
        self.whistle_active = False
    
    def query_status(self):
        """Queries the current status of the locomotive"""
        if not self.rocrail.is_connected:
            return False
            
        # Create query command
        lc_cmd = f'<lc id="{self.loco_id}" cmd="query"/>'
        
        # Send command
        return self.rocrail.send_command(lc_cmd)
    
    def set_speed(self, speed):
        """Sets locomotive speed
        
        Args:
            speed: Speed (0-100)
        
        Returns:
            True on success, False on error
        """
        # Check connection
        if not self.rocrail.is_connected:
            print("No RocRail connection")
            return False
        
        try:
            # Limit speed range
            speed = max(0, min(100, speed))
            
            # Use direction
            dir_param = f' dir="{1 if self.current_direction else 0}"'
            
            # Create XML command
            lc_cmd = f'<lc id="{self.loco_id}" V="{speed}"{dir_param}/>'
            
            # Send command
            if self.rocrail.send_command(lc_cmd):
                # Save current speed
                self.current_speed = speed
                print(f"Loco {self.loco_id}: Speed set to {speed}%")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error setting speed: {e}")
            # Clean up memory
            gc.collect()
            return False
    
    def set_direction(self, forward=True):
        """Sets locomotive direction
        
        Args:
            forward: True for forward, False for reverse
        
        Returns:
            True on success, False on error
        """
        if not self.rocrail.is_connected:
            print("No RocRail connection")
            return False
            
        try:
            # Create XML command
            lc_cmd = f'<lc id="{self.loco_id}" dir="{1 if forward else 0}"/>'
            
            # Send command
            if self.rocrail.send_command(lc_cmd):
                # Save current direction
                self.current_direction = forward
                print(f"Loco {self.loco_id}: Direction set to {'forward' if forward else 'reverse'}")
                return True
                
            return False
            
        except Exception as e:
            print(f"Error setting direction: {e}")
            return False
    
    def toggle_direction(self):
        """Toggle locomotive direction"""
        if not self.rocrail.is_connected:
            print("No RocRail connection")
            return False
            
        try:
            # Reverse direction
            self.current_direction = not self.current_direction
            
            # Send new direction command
            dir_value = 1 if self.current_direction else 0
            lc_cmd = f'<lc id="{self.loco_id}" dir="{dir_value}"/>'
            
            if self.rocrail.send_command(lc_cmd):
                print(f"Loco {self.loco_id}: Direction changed to {'forward' if self.current_direction else 'reverse'}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error changing direction: {e}")
            return False
    
    def toggle_light(self):
        """Toggle light on/off"""
        if not self.rocrail.is_connected:
            print("No RocRail connection")
            return False
            
        try:
            # Toggle light state
            self.light_on = not self.light_on
            
            # Function bit 0 is typically light
            fn_value = "true" if self.light_on else "false"
            lc_cmd = f'<fn id="{self.loco_id}" fn1="{fn_value}"/>'
            
            if self.rocrail.send_command(lc_cmd):
                print(f"Loco {self.loco_id}: Light {'on' if self.light_on else 'off'}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error toggling light: {e}")
            return False
    
    def toggle_sound(self):
        """Toggle sound on/off (Fn1)"""
        if not self.rocrail.is_connected:
            print("No RocRail connection")
            return False
            
        try:
            # Toggle sound state
            self.sound_on = not self.sound_on
            
            # Function bit 1 for sound
            fn_value = "2" if self.sound_on else "0"  # Bit 1 = 2^1 = 2
            lc_cmd = f'<lc id="{self.loco_id}" fn="{fn_value}"/>'
            
            if self.rocrail.send_command(lc_cmd):
                print(f"Loco {self.loco_id}: Sound {'on' if self.sound_on else 'off'}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error toggling sound: {e}")
            return False
    
    def activate_whistle(self, activate=True):
        """Activate/deactivate whistle (Fn2)"""
        if not self.rocrail.is_connected:
            print("No RocRail connection")
            return False
            
        try:
            # Set whistle state
            self.whistle_active = activate
            
            # Function bit 2 for whistle
            fn_value = "4" if activate else "0"  # Bit 2 = 2^2 = 4
            lc_cmd = f'<lc id="{self.loco_id}" fn="{fn_value}"/>'
            
            if self.rocrail.send_command(lc_cmd):
                print(f"Loco {self.loco_id}: Whistle {'activated' if activate else 'deactivated'}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error activating whistle: {e}")
            return False
    
    def emergency_stop(self):
        """Emergency stop for the locomotive"""
        return self.set_speed(0)
    
    def check_updates(self):
        """Checks for updates from RocRail about locomotive status
        
        Returns:
            True if updates were processed, False otherwise
        """
        if not self.rocrail.is_connected:
            return False
            
        # Get received data
        data = self.rocrail.receive_data(timeout=0)
        if not data:
            return False
            
        try:
            # Convert bytes to string
            try:
                buffer_str = data.decode('utf-8')
            except:
                # If decoding fails, trim buffer and try again later
                self.rocrail.limit_buffer(512)
                return False
            
            # Early filtering: Check if there are any locomotive info
            if f'id="{self.loco_id}"' not in buffer_str:
                # No relevant info, reduce buffer to save memory
                self.rocrail.limit_buffer(1024)
                return False
            
            # Process locomotive info
            changes = False
            
            # Find locomotive position
            v_pos = buffer_str.find(f'id="{self.loco_id}"')
            if v_pos > 0:
                # Look for speed parameter
                v_start = buffer_str.find('V="', v_pos)
                if v_start > 0:
                    v_end = buffer_str.find('"', v_start + 3)
                    if v_end > v_start:
                        try:
                            new_speed = int(buffer_str[v_start + 3:v_end])
                            if new_speed != self.current_speed:
                                self.current_speed = new_speed
                                print(f"External speed change: {new_speed}%")
                                changes = True
                        except ValueError:
                            pass
            
                # Look for direction parameter
                dir_start = buffer_str.find('dir="', v_pos)
                if dir_start > 0:
                    dir_end = buffer_str.find('"', dir_start + 5)
                    if dir_end > dir_start:
                        try:
                            dir_value = buffer_str[dir_start + 5:dir_end]
                            new_dir = dir_value == "1"
                            if new_dir != self.current_direction:
                                self.current_direction = new_dir
                                print(f"External direction change: {'forward' if new_dir else 'reverse'}")
                                changes = True
                        except:
                            pass
                
                # Look for light status
                fn_start = buffer_str.find('fn="', v_pos)
                if fn_start > 0:
                    fn_end = buffer_str.find('"', fn_start + 4)
                    if fn_end > fn_start:
                        try:
                            fn_value = buffer_str[fn_start + 4:fn_end]
                            new_light = '1' in fn_value  # Bit 0 for light
                            if new_light != self.light_on:
                                self.light_on = new_light
                                print(f"External light change: {'on' if new_light else 'off'}")
                                changes = True
                        except:
                            pass
            
            # Trim buffer - remove processed part
            end_pos = buffer_str.find('</lc>', v_pos)
            if end_pos > 0:
                # Remove up to this position
                self.rocrail.recv_buffer = self.rocrail.recv_buffer[end_pos + 5:]
            else:
                # If no end found, significantly reduce buffer
                self.rocrail.limit_buffer(256)
                
            # Ensure buffer doesn't grow too large
            self.rocrail.limit_buffer(2048)
            
            # Run garbage collection for large buffers
            if len(self.rocrail.recv_buffer) > 1024:
                gc.collect()
                
            return changes
            
        except Exception as e:
            print(f"Error parsing locomotive data: {e}")
            # Reset buffer on error
            self.rocrail.clear_buffer()
            # Free up memory
            gc.collect()
            return False
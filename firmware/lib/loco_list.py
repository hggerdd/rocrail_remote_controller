# lib/loco_list.py
import json
import gc

class LocoList:
    """Manages a list of locomotives with selection functionality"""
    
    def __init__(self, filename="loco_list.txt"):
        """Initialize locomotive list
        
        Args:
            filename: File to store locomotive list persistently
        """
        self.filename = filename
        self.locomotives = []
        self.selected_index = 0
        self.max_locos = 5  # Limited by NeoPixel LEDs (1-5)
        
        # Try to load existing list
        self.load_from_file()
    
    def add_locomotive(self, loco_id, loco_name=None):
        """Add locomotive to the list
        
        Args:
            loco_id: Locomotive ID
            loco_name: Optional display name (uses ID if not provided)
        """
        if loco_name is None:
            loco_name = loco_id
            
        # Check if already exists
        for loco in self.locomotives:
            if loco['id'] == loco_id:
                return False
                
        # Add if we have space
        if len(self.locomotives) < self.max_locos:
            self.locomotives.append({
                'id': loco_id,
                'name': loco_name
            })
            self._sort_alphabetically()
            return True
        return False
    
    def _sort_alphabetically(self):
        """Sort locomotives alphabetically by name"""
        self.locomotives.sort(key=lambda x: x['name'].upper())
        # Reset selection to first locomotive after sorting
        self.selected_index = 0
    
    def get_selected_locomotive(self):
        """Get currently selected locomotive
        
        Returns:
            Dict with 'id' and 'name' or None if empty list
        """
        if self.locomotives and 0 <= self.selected_index < len(self.locomotives):
            return self.locomotives[self.selected_index]
        return None
    
    def get_selected_id(self):
        """Get ID of currently selected locomotive
        
        Returns:
            String locomotive ID or None
        """
        loco = self.get_selected_locomotive()
        return loco['id'] if loco else None
    
    def select_next(self):
        """Select next locomotive in list
        
        Returns:
            True if selection changed, False otherwise
        """
        if len(self.locomotives) <= 1:
            return False
            
        old_index = self.selected_index
        self.selected_index = (self.selected_index + 1) % len(self.locomotives)
        return old_index != self.selected_index
    
    def select_previous(self):
        """Select previous locomotive in list
        
        Returns:
            True if selection changed, False otherwise
        """
        if len(self.locomotives) <= 1:
            return False
            
        old_index = self.selected_index
        self.selected_index = (self.selected_index - 1) % len(self.locomotives)
        return old_index != self.selected_index
    
    def select_by_index(self, index):
        """Select locomotive by index
        
        Args:
            index: Index to select
            
        Returns:
            True if selection changed, False otherwise
        """
        if 0 <= index < len(self.locomotives):
            old_index = self.selected_index
            self.selected_index = index
            return old_index != self.selected_index
        return False
    
    def get_count(self):
        """Get number of locomotives in list"""
        return len(self.locomotives)
    
    def get_selected_index(self):
        """Get index of currently selected locomotive"""
        return self.selected_index
    
    def clear(self):
        """Clear all locomotives"""
        self.locomotives = []
        self.selected_index = 0
    
    def save_to_file(self):
        """Save locomotive list to file"""
        try:
            data = {
                'locomotives': self.locomotives,
                'selected_index': self.selected_index
            }
            with open(self.filename, 'w') as f:
                json.dump(data, f)
            print(f"Locomotive list saved to {self.filename}")
            return True
        except Exception as e:
            print(f"Error saving locomotive list: {e}")
            return False
    
    def load_from_file(self):
        """Load locomotive list from file"""
        try:
            with open(self.filename, 'r') as f:
                data = json.load(f)
            
            self.locomotives = data.get('locomotives', [])
            self.selected_index = data.get('selected_index', 0)
            
            # Validate selected_index
            if self.selected_index >= len(self.locomotives):
                self.selected_index = 0
                
            print(f"Locomotive list loaded from {self.filename}: {len(self.locomotives)} locomotives")
            return True
        except Exception as e:
            print(f"Could not load locomotive list: {e}")
            # Initialize with default locomotive if file doesn't exist
            self.locomotives = []
            self.selected_index = 0
            return False
    
    def update_from_rocrail_response(self, xml_response):
        """Update locomotive list from RocRail query response
        
        Args:
            xml_response: XML string response from RocRail
            
        Returns:
            True if locomotives were updated, False otherwise
        """
        try:
            # Debug: Print what we're trying to parse
            print(f"[LOCO_PARSE] Attempting to parse {len(xml_response)} chars")
            
            # Check if we have a complete lclist structure
            if '<lclist>' not in xml_response or '</lclist>' not in xml_response:
                print("[LOCO_PARSE] Incomplete lclist structure - waiting for more data")
                return False
            
            # Extract the complete lclist section
            start_idx = xml_response.find('<lclist>')
            end_idx = xml_response.find('</lclist>') + len('</lclist>')
            
            if start_idx == -1 or end_idx == -1:
                print("[LOCO_PARSE] Could not find complete lclist boundaries")
                return False
            
            lclist_section = xml_response[start_idx:end_idx]
            print(f"[LOCO_PARSE] Extracted lclist section: {len(lclist_section)} chars")
            
            # Use the new intelligent locomotive extraction
            extraction_result = self.extract_locomotives_from_lclist(lclist_section)
            locomotives_found = extraction_result['locomotives']
            
            print(f"[LOCO_PARSE] Extraction result: {extraction_result['total_found']} locomotives from {extraction_result['entries_processed']} entries")
            
            if locomotives_found:
                # Clear existing list and add new locomotives
                old_count = len(self.locomotives)
                self.clear()
                
                # Add locomotives (up to max limit)
                added = 0
                for loco_info in locomotives_found:
                    if self.add_locomotive(loco_info['id'], loco_info['name']):
                        added += 1
                        print(f"[LOCO_PARSE] Added: {loco_info['name']} (ID: {loco_info['id']})")
                        if added >= self.max_locos:
                            print(f"[LOCO_PARSE] Reached maximum locomotives limit ({self.max_locos})")
                            break
                
                # Save updated list if we added any
                if added > 0:
                    self.save_to_file()
                    print(f"[LOCO_PARSE] ✅ Successfully updated locomotive list: {old_count} -> {added} locos")
                    print(f"[LOCO_PARSE] Final list: {', '.join([loco['name'] for loco in self.locomotives])}")
                    return True
                else:
                    print("[LOCO_PARSE] ❌ No locomotives were added to the list")
                    return False
            else:
                print("[LOCO_PARSE] ❌ No valid locomotives found in lclist")
                return False
                
        except Exception as e:
            print(f"[LOCO_PARSE] ❌ Error parsing locomotives: {e}")
            return False
        finally:
            gc.collect()
    
    def extract_locomotives_from_lclist(self, lclist_xml):
        """Extract locomotives specifically from lclist XML (locomotive definitions, not status updates)
        
        Args:
            lclist_xml: XML string containing lclist structure
            
        Returns:
            Dict with locomotive information: {'locomotives': [list], 'total_found': int}
        """
        try:
            locomotives_found = []
            
            print(f"[LOCO_EXTRACT] Processing lclist XML: {len(lclist_xml)} chars")
            print(f"[LOCO_EXTRACT] Sample: {lclist_xml[:200]}...")
            
            # Look for locomotive definition entries (not status updates)
            text = lclist_xml
            start_pos = 0
            loco_count = 0
            
            while True:
                # Find <lc entry
                lc_pos = text.find('<lc ', start_pos)
                if lc_pos == -1:
                    break
                
                # Find the end of this locomotive entry (either /> or </lc> or next <lc)
                entry_end = text.find('/>', lc_pos)
                next_lc = text.find('<lc ', lc_pos + 4)
                
                # Determine the actual end of this entry
                if entry_end != -1 and (next_lc == -1 or entry_end < next_lc):
                    lc_entry = text[lc_pos:entry_end + 2]
                elif next_lc != -1:
                    lc_entry = text[lc_pos:next_lc]
                else:
                    # Take rest of text
                    lc_entry = text[lc_pos:]
                
                loco_count += 1
                print(f"[LOCO_EXTRACT] Processing locomotive entry {loco_count}: {lc_entry[:100]}...")
                
                # Extract locomotive information from this entry
                loco_info = self._extract_loco_info_from_entry(lc_entry)
                if loco_info:
                    locomotives_found.append(loco_info)
                    print(f"[LOCO_EXTRACT] ✓ Found locomotive: {loco_info}")
                else:
                    print(f"[LOCO_EXTRACT] ✗ Could not extract info from entry")
                
                # Move to next entry
                if next_lc != -1:
                    start_pos = next_lc
                else:
                    break
            
            print(f"[LOCO_EXTRACT] Total entries processed: {loco_count}")
            print(f"[LOCO_EXTRACT] Valid locomotives extracted: {len(locomotives_found)}")
            
            return {
                'locomotives': locomotives_found,
                'total_found': len(locomotives_found),
                'entries_processed': loco_count
            }
                
        except Exception as e:
            print(f"[LOCO_EXTRACT] Error extracting locomotives: {e}")
            return {'locomotives': [], 'total_found': 0, 'entries_processed': 0}
    
    def _extract_loco_info_from_entry(self, lc_entry):
        """Extract locomotive info from a single <lc> entry
        
        Args:
            lc_entry: Single locomotive XML entry
            
        Returns:
            Dict with locomotive info or None if not a valid locomotive definition
        """
        try:
            # Check if this is a locomotive definition (not a status update)
            # Locomotive definitions have attributes like: image, roadname, desc, dectype
            # Status updates have attributes like: V, dir, server, placing
            
            has_definition_attrs = any(attr in lc_entry for attr in [
                'image=', 'roadname=', 'desc=', 'dectype=', 'owner=', 'color=', 'number='
            ])
            
            has_status_attrs = any(attr in lc_entry for attr in [
                'V=', 'dir=', 'server=', 'placing=', 'runtime=', 'throttleid='
            ])
            
            # Skip status updates - we only want locomotive definitions
            if has_status_attrs and not has_definition_attrs:
                print(f"[LOCO_EXTRACT] Skipping status update entry")
                return None
            
            # Extract ID (primary identifier)
            loco_id = self._extract_attribute(lc_entry, 'id')
            
            # Extract shortid (secondary identifier)
            loco_shortid = self._extract_attribute(lc_entry, 'shortid')
            
            # Extract additional info
            loco_roadname = self._extract_attribute(lc_entry, 'roadname')
            loco_number = self._extract_attribute(lc_entry, 'number')
            
            # Determine the best identifier
            identifier = None
            display_name = None
            
            if loco_id and loco_id.strip() and loco_id != 'model':
                identifier = loco_id.strip()
                display_name = identifier
            elif loco_shortid and loco_shortid.strip():
                identifier = loco_shortid.strip()
                display_name = identifier
            
            # Enhance display name with additional info
            if identifier and loco_roadname and loco_roadname.strip():
                display_name = f"{identifier} ({loco_roadname.strip()})"
            elif identifier and loco_number and loco_number.strip():
                display_name = f"{identifier} #{loco_number.strip()}"
            
            if identifier:
                return {
                    'id': identifier,
                    'name': display_name or identifier,
                    'shortid': loco_shortid or '',
                    'roadname': loco_roadname or '',
                    'number': loco_number or ''
                }
            else:
                print(f"[LOCO_EXTRACT] No valid identifier found in entry")
                return None
                
        except Exception as e:
            print(f"[LOCO_EXTRACT] Error processing locomotive entry: {e}")
            return None
    
    def _extract_attribute(self, xml_text, attr_name):
        """Extract attribute value from XML text
        
        Args:
            xml_text: XML text containing the attribute
            attr_name: Name of attribute to extract
            
        Returns:
            Attribute value or None if not found
        """
        try:
            pattern = f'{attr_name}="'
            start_pos = xml_text.find(pattern)
            if start_pos == -1:
                return None
            
            value_start = start_pos + len(pattern)
            value_end = xml_text.find('"', value_start)
            if value_end == -1:
                return None
            
            return xml_text[value_start:value_end]
        except:
            return None
    
    def get_status_string(self):
        """Get status string for debugging
        
        Returns:
            String with locomotive list status
        """
        if not self.locomotives:
            return "No locomotives available"
        
        selected = self.get_selected_locomotive()
        return f"Loco {self.selected_index + 1}/{len(self.locomotives)}: {selected['name']} ({selected['id']})"

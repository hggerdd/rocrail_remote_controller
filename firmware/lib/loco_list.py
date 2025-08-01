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
            print("="*50)
            print("LOCOMOTIVE LIST PARSING DEBUG")
            print("="*50)
            print(f"XML Response Length: {len(xml_response)} characters")
            print(f"First 500 chars: {xml_response[:500]}")
            if len(xml_response) > 500:
                print(f"Last 200 chars: {xml_response[-200:]}")
            print("-"*50)
            
            # Simple XML parsing for locomotive entries
            # Look for <lc id="..." patterns
            import re
            
            old_count = len(self.locomotives)
            locomotives_found = []
            
            print("SEARCHING FOR LOCOMOTIVE PATTERNS...")
            
            # Pattern 1: <lc id="locomotivename" ...>
            lc_pattern1 = r'<lc\s+id="([^"]+)"[^>]*>'
            matches1 = re.findall(lc_pattern1, xml_response)
            print(f"Pattern 1 '<lc id=\"...\">': Found {len(matches1)} matches: {matches1}")
            locomotives_found.extend(matches1)
            
            # Pattern 2: id="locomotivename" (anywhere in lc tag)
            lc_pattern2 = r'id="([^"]+)"[^>]*(?:/>|>)'
            matches2 = re.findall(lc_pattern2, xml_response)
            print(f"Pattern 2 'id=\"...\"': Found {len(matches2)} matches: {matches2}")
            locomotives_found.extend(matches2)
            
            # Pattern 3: Look for locomotive names in different XML structures
            # Some RocRail responses might use different formats
            loco_pattern3 = r'locomotive[^>]*id="([^"]+)"'
            matches3 = re.findall(loco_pattern3, xml_response)
            print(f"Pattern 3 'locomotive id=\"...\"': Found {len(matches3)} matches: {matches3}")
            locomotives_found.extend(matches3)
            
            # Pattern 4: Look for model elements (lclist response format)
            model_pattern = r'<lc[^>]*id="([^"]+)"[^>]*'
            matches4 = re.findall(model_pattern, xml_response)
            print(f"Pattern 4 '<lc...id=\"...\">': Found {len(matches4)} matches: {matches4}")
            locomotives_found.extend(matches4)
            
            print(f"Total raw matches found: {len(locomotives_found)}")
            print(f"Raw locomotive IDs: {locomotives_found}")
            print("-"*50)
            
            # Remove duplicates and filter valid locomotive IDs
            unique_locomotives = []
            for loco_id in locomotives_found:
                loco_id = loco_id.strip()
                print(f"Processing locomotive ID: '{loco_id}'")
                
                # Filter out obvious non-locomotive entries
                if (loco_id and 
                    len(loco_id) > 0 and 
                    loco_id not in unique_locomotives and
                    not loco_id.startswith('xml') and
                    not loco_id.startswith('query') and
                    not loco_id.startswith('model') and
                    (not loco_id.isdigit() or len(loco_id) > 3)):  # Allow digits if longer than 3 chars
                    unique_locomotives.append(loco_id)
                    print(f"  ✓ Added: '{loco_id}'")
                else:
                    print(f"  ✗ Filtered out: '{loco_id}'")
            
            print(f"Filtered unique locomotives: {unique_locomotives}")
            print("-"*50)
            
            # Add locomotives if we found any new ones
            if unique_locomotives:
                print(f"Current locomotive count: {len(self.locomotives)}")
                print(f"Found locomotive count: {len(unique_locomotives)}")
                
                # Clear existing list only if we found substantial new data
                if len(unique_locomotives) > len(self.locomotives):
                    print("Found more locomotives, updating list...")
                    self.clear()
                
                # Add locomotives (up to max limit)
                added = 0
                for loco_id in unique_locomotives:
                    if self.add_locomotive(loco_id):
                        added += 1
                        print(f"✓ Added locomotive: {loco_id}")
                        if added >= self.max_locos:
                            print(f"Reached maximum locomotive limit ({self.max_locos})")
                            break
                    else:
                        print(f"✗ Failed to add locomotive: {loco_id}")
                
                # Save updated list if we added any
                if added > 0:
                    self.save_to_file()
                    print(f"*** SUCCESS: Updated locomotive list: {added} locomotives added, total: {len(self.locomotives)} ***")
                    print("="*50)
                    return True
                else:
                    print("*** NO NEW LOCOMOTIVES ADDED (might already exist in list) ***")
                    print("="*50)
                    return False
            else:
                print("*** NO LOCOMOTIVE PATTERNS FOUND IN XML RESPONSE ***")
                print("="*50)
                return False
                
        except Exception as e:
            print(f"*** ERROR PARSING ROCRAIL RESPONSE: {e} ***")
            print("="*50)
            return False
        finally:
            gc.collect()
    
    def get_status_string(self):
        """Get status string for debugging
        
        Returns:
            String with locomotive list status
        """
        if not self.locomotives:
            return "No locomotives available"
        
        selected = self.get_selected_locomotive()
        return f"Loco {self.selected_index + 1}/{len(self.locomotives)}: {selected['name']} ({selected['id']})"

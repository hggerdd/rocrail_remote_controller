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
            # Only show detailed parsing if we find lclist
            if 'lclist' in xml_response.lower():
                print("="*50)
                print("PARSING LOCOMOTIVE LIST RESPONSE")
                print("="*50)
                print(f"Response length: {len(xml_response)} chars")
                if len(xml_response) < 1000:
                    print(f"Full response: {xml_response}")
                else:
                    print(f"First 500 chars: {xml_response[:500]}")
                    print(f"Last 200 chars: {xml_response[-200:]}")
                print("-"*50)
            
            # Simple string-based parsing (no regex needed)
            locomotives_found = []
            
            # Look for locomotive entries using string methods
            # Pattern 1: <lc id="..." - most common
            text = xml_response
            start_pos = 0
            while True:
                # Find <lc id=" pattern
                lc_pos = text.find('<lc ', start_pos)
                if lc_pos == -1:
                    break
                    
                # Find id=" after the <lc
                id_pos = text.find('id="', lc_pos)
                if id_pos == -1:
                    start_pos = lc_pos + 4
                    continue
                    
                # Find the end quote
                id_start = id_pos + 4
                id_end = text.find('"', id_start)
                if id_end == -1:
                    start_pos = lc_pos + 4
                    continue
                
                # Extract locomotive ID
                loco_id = text[id_start:id_end].strip()
                if loco_id:
                    locomotives_found.append(loco_id)
                    if 'lclist' in xml_response.lower():
                        print(f"Found locomotive: {loco_id}")
                
                start_pos = id_end
            
            # Filter out duplicates and invalid entries
            unique_locomotives = []
            for loco_id in locomotives_found:
                if (loco_id and 
                    len(loco_id) > 0 and 
                    loco_id not in unique_locomotives and
                    not loco_id.startswith('xml') and
                    not loco_id.startswith('query') and
                    not loco_id.startswith('model') and
                    loco_id != 'model'):  # Filter out system entries
                    unique_locomotives.append(loco_id)
            
            if unique_locomotives:
                print(f"Valid locomotives found: {unique_locomotives}")
                
                # Clear existing list only if we found substantial new data
                if len(unique_locomotives) > len(self.locomotives):
                    print("Updating locomotive list...")
                    self.clear()
                
                # Add locomotives (up to max limit)
                added = 0
                for loco_id in unique_locomotives:
                    if self.add_locomotive(loco_id):
                        added += 1
                        if added >= self.max_locos:
                            break
                
                # Save updated list if we added any
                if added > 0:
                    self.save_to_file()
                    print(f"Added {added} locomotives, total: {len(self.locomotives)}")
                    return True
                else:
                    print("No new locomotives added")
                    return False
            else:
                if 'lclist' in xml_response.lower():
                    print("No locomotive IDs found in lclist response")
                return False
                
        except Exception as e:
            print(f"Error parsing locomotive response: {e}")
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

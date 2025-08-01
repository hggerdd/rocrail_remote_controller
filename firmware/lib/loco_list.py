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
            # Simple XML parsing for locomotive entries
            # Look for <lc id="..." patterns
            import re
            
            # Clear existing list
            old_count = len(self.locomotives)
            self.clear()
            
            # Find all locomotive entries
            lc_pattern = r'<lc\s+id="([^"]+)"[^>]*>'
            matches = re.findall(lc_pattern, xml_response)
            
            # Add locomotives (up to max limit)
            added = 0
            for loco_id in matches:
                if self.add_locomotive(loco_id):
                    added += 1
                    if added >= self.max_locos:
                        break
            
            # Save updated list
            if added > 0:
                self.save_to_file()
                print(f"Updated locomotive list: {added} locomotives found")
                return True
            else:
                print("No locomotives found in RocRail response")
                return False
                
        except Exception as e:
            print(f"Error parsing RocRail response: {e}")
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

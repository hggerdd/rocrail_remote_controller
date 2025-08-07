"""
Simple Button Debug Test
Check raw button states without debouncing
"""

import asyncio
import time
from machine import Pin
from hardware_config import *

async def test_raw_buttons():
    """Test raw button readings to debug the issue"""
    print("=== Raw Button State Test ===")
    print("This will show the raw pin values to debug button issues")
    print("Press Ctrl+C to exit\n")
    
    # Initialize buttons directly
    buttons = {
        'emergency': Pin(BTN_NOTHALT, Pin.IN, Pin.PULL_UP),
        'direction': Pin(BTN_RICHTUNGSWECHEL, Pin.IN, Pin.PULL_UP), 
        'sound': Pin(BTN_GELB, Pin.IN, Pin.PULL_UP),
        'light': Pin(BTN_BLAU, Pin.IN, Pin.PULL_UP),
        'btn_up': Pin(BTN_MITTE_UP, Pin.IN, Pin.PULL_UP),
        'btn_down': Pin(BTN_MITTE_DOWN, Pin.IN, Pin.PULL_UP)
    }
    
    print("Button pins initialized")
    print("Pin values: 1 = not pressed (pull-up), 0 = pressed")
    print("Monitoring raw pin states...\n")
    
    last_states = {}
    for name in buttons:
        last_states[name] = buttons[name].value()
    
    try:
        while True:
            # Check each button
            for name, pin in buttons.items():
                current_value = pin.value()
                
                # Report state changes
                if current_value != last_states[name]:
                    if current_value == 0:
                        print(f"🔘 {name.upper()} PRESSED (1→0)")
                    else:
                        print(f"🔸 {name.upper()} RELEASED (0→1)")
                    last_states[name] = current_value
            
            await asyncio.sleep(0.01)  # 10ms polling
            
    except KeyboardInterrupt:
        print("\nRaw button test ended")
        
        # Show final pin states
        print("\nFinal pin states:")
        for name, pin in buttons.items():
            value = pin.value()
            state = "not pressed" if value == 1 else "PRESSED"
            print(f"  {name}: {value} ({state})")

def run_raw_test():
    """Run the raw button test"""
    try:
        if hasattr(asyncio, 'run'):
            asyncio.run(test_raw_buttons())
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(test_raw_buttons())
    except Exception as e:
        print(f"Raw button test failed: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    run_raw_test()

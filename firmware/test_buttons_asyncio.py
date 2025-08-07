"""
Button Test for AsyncIO Hardware Manager
Test all buttons to ensure they work correctly
"""

import asyncio
import time
from hardware_config import *
from lib.async_controllers.async_hardware import AsyncHardwareManager

async def test_buttons():
    """Test all buttons with real-time feedback"""
    print("=== AsyncIO Button Test ===")
    print("Testing all buttons - press each button to verify it works")
    print("Press Ctrl+C to exit\n")
    
    # Initialize hardware
    hardware = AsyncHardwareManager()
    if not await hardware.initialize():
        print("Hardware initialization failed!")
        return False
        
    print("Hardware initialized successfully")
    print("Button mapping:")
    print(f"  Emergency (red): Pin {BTN_NOTHALT}")
    print(f"  Direction (green): Pin {BTN_RICHTUNGSWECHEL}")
    print(f"  Sound (yellow): Pin {BTN_GELB}")
    print(f"  Light (blue): Pin {BTN_BLAU}")
    print(f"  Up (black): Pin {BTN_MITTE_UP}")
    print(f"  Down (black): Pin {BTN_MITTE_DOWN}")
    print(f"  Speed pot: Pin {ADC_GESCHWINDIGKEIT}")
    print("\nPress buttons now...\n")
    
    button_names = {
        'emergency': 'EMERGENCY (RED)',
        'direction': 'DIRECTION (GREEN)', 
        'sound': 'SOUND (YELLOW)',
        'light': 'LIGHT (BLUE)',
        'btn_up': 'UP (BLACK)',
        'btn_down': 'DOWN (BLACK)'
    }
    
    last_speed = -1
    
    try:
        while True:
            # Read all inputs
            inputs = await hardware.read_all_inputs()
            
            # Check for button presses
            for button_key, pressed in inputs.items():
                if button_key == 'speed':
                    continue
                    
                if pressed:
                    button_display = button_names.get(button_key, button_key.upper())
                    print(f"🔘 {button_display} PRESSED!")
                    
            # Show speed changes with calibration info
            speed = inputs['speed']
            if abs(speed - last_speed) > 2:  # Only show significant changes
                # Get raw ADC for debugging
                raw_adc = await hardware.get_raw_adc()
                calibration = hardware.get_poti_calibration()
                
                print(f"🎛️  Speed: {speed} (Raw: {raw_adc}, Range: {calibration['min_value']}-{calibration['max_value']})")
                last_speed = speed
                
            # Small delay
            await asyncio.sleep(0.05)  # 50ms polling
            
    except KeyboardInterrupt:
        print("\n\nButton test ended")
        return True
    except Exception as e:
        print(f"Button test error: {e}")
        return False

async def test_individual_buttons():
    """Test buttons one by one with detailed feedback"""
    print("=== Individual Button Test ===")
    
    hardware = AsyncHardwareManager()
    if not await hardware.initialize():
        print("Hardware initialization failed!")
        return False
    
    # Test each button individually
    buttons_to_test = [
        ('emergency', 'EMERGENCY (RED)', BTN_NOTHALT),
        ('direction', 'DIRECTION (GREEN)', BTN_RICHTUNGSWECHEL),
        ('sound', 'SOUND (YELLOW)', BTN_GELB),
        ('light', 'LIGHT (BLUE)', BTN_BLAU),
        ('btn_up', 'UP (BLACK)', BTN_MITTE_UP),
        ('btn_down', 'DOWN (BLACK)', BTN_MITTE_DOWN)
    ]
    
    for button_key, display_name, pin_num in buttons_to_test:
        print(f"\nTesting {display_name} (Pin {pin_num})")
        print("Press the button within 10 seconds...")
        
        start_time = time.ticks_ms()
        timeout = 10000  # 10 seconds
        button_detected = False
        
        while time.ticks_diff(time.ticks_ms(), start_time) < timeout:
            inputs = await hardware.read_all_inputs()
            
            if inputs[button_key]:
                print(f"✓ {display_name} WORKING!")
                button_detected = True
                break
                
            await asyncio.sleep(0.05)
            
        if not button_detected:
            print(f"✗ {display_name} - No press detected")
            print(f"   Check wiring on Pin {pin_num}")
            
        await asyncio.sleep(0.5)  # Brief pause between tests
        
    return True

def run_button_test():
    """Run button tests with MicroPython compatibility"""
    try:
        print("Choose test mode:")
        print("1. Real-time button test (press any button)")
        print("2. Individual button test (guided)")
        
        # For automation, default to real-time test
        test_mode = 1
        
        if test_mode == 1:
            if hasattr(asyncio, 'run'):
                asyncio.run(test_buttons())
            else:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(test_buttons())
        else:
            if hasattr(asyncio, 'run'):
                asyncio.run(test_individual_buttons())
            else:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(test_individual_buttons())
                
    except Exception as e:
        print(f"Button test failed: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    run_button_test()

"""
Potentiometer Calibration Test for AsyncIO Hardware
Test the calibrated potentiometer reading with your specific range
"""

import asyncio
import time
from lib.async_controllers.async_hardware import AsyncHardwareManager

async def test_poti_calibration():
    """Test potentiometer calibration with real-time feedback"""
    print("=== Potentiometer Calibration Test ===")
    print(f"Calibrated range: 1310 - 2360 (raw ADC)")
    print(f"Output range: 0 - 100 (locomotive speed)")
    print("Turn the potentiometer to test calibration")
    print("Press Ctrl+C to exit\n")
    
    # Initialize hardware
    hardware = AsyncHardwareManager()
    if not await hardware.initialize():
        print("Hardware initialization failed!")
        return False
        
    print("Hardware initialized successfully")
    print("Reading potentiometer values...\n")
    print("Raw ADC | Normalized | Status")
    print("-" * 35)
    
    last_speed = -1
    
    try:
        while True:
            # Get raw ADC value directly for debugging
            raw_adc = hardware.speed_adc.read()
            
            # Get normalized speed through hardware manager
            inputs = await hardware.read_all_inputs()
            normalized_speed = inputs['speed']
            
            # Only print when speed changes significantly
            if abs(normalized_speed - last_speed) > 1:
                # Determine status
                if raw_adc < hardware.POTI_MIN_VALUE:
                    status = "Below min"
                elif raw_adc > hardware.POTI_MAX_VALUE:
                    status = "Above max" 
                else:
                    status = "In range"
                    
                print(f"{raw_adc:7d} | {normalized_speed:10d} | {status}")
                last_speed = normalized_speed
                
            await asyncio.sleep(0.1)  # 100ms update rate
            
    except KeyboardInterrupt:
        print(f"\nPotentiometer test ended")
        
        # Show final reading
        final_raw = hardware.speed_adc.read()
        final_normalized = hardware._normalize_speed(final_raw)
        print(f"\nFinal reading:")
        print(f"Raw ADC: {final_raw}")
        print(f"Normalized: {final_normalized}")
        print(f"Range coverage: {((final_normalized / 100) * 100):.1f}%")

async def test_poti_range():
    """Test the full potentiometer range"""
    print("=== Potentiometer Range Test ===")
    print("This will help verify your potentiometer calibration")
    print("\nInstructions:")
    print("1. Turn potentiometer to minimum position")
    print("2. Note the raw ADC value")  
    print("3. Turn potentiometer to maximum position")
    print("4. Note the raw ADC value")
    print("5. Compare with calibrated values (1310-2360)")
    print("\nPress Ctrl+C when done\n")
    
    hardware = AsyncHardwareManager()
    if not await hardware.initialize():
        print("Hardware initialization failed!")
        return False
        
    min_seen = 4095
    max_seen = 0
    
    try:
        while True:
            raw_adc = hardware.speed_adc.read()
            
            if raw_adc < min_seen:
                min_seen = raw_adc
                print(f"New minimum: {min_seen}")
                
            if raw_adc > max_seen:
                max_seen = raw_adc
                print(f"New maximum: {max_seen}")
                
            await asyncio.sleep(0.05)
            
    except KeyboardInterrupt:
        print(f"\nRange test results:")
        print(f"Observed range: {min_seen} - {max_seen}")
        print(f"Calibrated range: {hardware.POTI_MIN_VALUE} - {hardware.POTI_MAX_VALUE}")
        print(f"Range difference: {abs(min_seen - hardware.POTI_MIN_VALUE)} to {abs(max_seen - hardware.POTI_MAX_VALUE)}")
        
        if abs(min_seen - hardware.POTI_MIN_VALUE) > 50 or abs(max_seen - hardware.POTI_MAX_VALUE) > 50:
            print("⚠️  Large difference detected - consider updating calibration values")
        else:
            print("✅ Calibration values look good")

def run_poti_test():
    """Run potentiometer test with MicroPython compatibility"""
    print("Choose test mode:")
    print("1. Real-time calibration test")
    print("2. Range verification test")
    
    # Default to calibration test for automation
    test_mode = 1
    
    try:
        if test_mode == 1:
            if hasattr(asyncio, 'run'):
                asyncio.run(test_poti_calibration())
            else:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(test_poti_calibration())
        else:
            if hasattr(asyncio, 'run'):
                asyncio.run(test_poti_range())
            else:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(test_poti_range())
                
    except Exception as e:
        print(f"Potentiometer test failed: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    run_poti_test()

"""
Minimal AsyncIO Button Test
Test the AsyncHardwareManager button reading directly
"""

import asyncio
from lib.async_controllers.async_hardware import AsyncHardwareManager

async def minimal_button_test():
    """Minimal test of AsyncHardwareManager button functionality"""
    print("=== Minimal AsyncIO Button Test ===")
    print("Testing AsyncHardwareManager directly")
    print("Press buttons to see if they register...")
    print("Press Ctrl+C to exit\n")
    
    # Initialize hardware manager
    hardware = AsyncHardwareManager()
    
    print("Initializing hardware...")
    if not await hardware.initialize():
        print("❌ Hardware initialization failed!")
        return
        
    print("✅ Hardware initialized successfully")
    print("Now press any button...\n")
    
    try:
        while True:
            # Read inputs
            inputs = await hardware.read_all_inputs()
            
            # The debug prints are now in the hardware manager
            # We don't need to check here - just keep the loop running
            
            # Small delay
            await asyncio.sleep(0.05)  # 50ms
            
    except KeyboardInterrupt:
        print("\nMinimal button test ended")

def run_minimal_test():
    """Run minimal button test"""
    try:
        if hasattr(asyncio, 'run'):
            asyncio.run(minimal_button_test())
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(minimal_button_test())
    except Exception as e:
        print(f"Minimal test failed: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    run_minimal_test()

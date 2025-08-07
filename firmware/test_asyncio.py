"""
Simple test script for asyncio controller components
"""

import asyncio
import sys
import time

# Test basic asyncio functionality
async def test_basic_asyncio():
    """Test basic asyncio functionality"""
    print("Testing basic asyncio...")
    
    # Test simple async task
    async def simple_task(name, delay):
        print(f"Task {name} starting")
        await asyncio.sleep(delay)
        print(f"Task {name} completed after {delay}s")
        return f"Result from {name}"
    
    # Run multiple tasks concurrently
    start_time = time.time()
    results = await asyncio.gather(
        simple_task("A", 1.0),
        simple_task("B", 0.5), 
        simple_task("C", 1.5)
    )
    end_time = time.time()
    
    print(f"All tasks completed in {end_time - start_time:.2f}s")
    print(f"Results: {results}")
    print("✓ Basic asyncio test passed")
    return True

# Test async state management
async def test_async_state():
    """Test async state management"""
    print("\nTesting async state management...")
    
    try:
        from lib.async_controllers.async_state import AsyncControllerState
        
        state = AsyncControllerState()
        
        # Test state changes
        await state.set_wifi_status("connecting")
        status = await state.get_wifi_status()
        assert status == "connecting", f"Expected 'connecting', got '{status}'"
        
        await state.set_rocrail_status("connected")
        rocrail_status = await state.get_rocrail_status()
        assert rocrail_status == "connected", f"Expected 'connected', got '{rocrail_status}'"
        
        # Test speed control
        assert await state.is_speed_enabled(), "Speed should be enabled by default"
        await state.disable_speed_sending()
        assert not await state.is_speed_enabled(), "Speed should be disabled"
        await state.enable_speed_sending()
        assert await state.is_speed_enabled(), "Speed should be re-enabled"
        
        print("✓ Async state management test passed")
        return True
        
    except Exception as e:
        print(f"✗ Async state test failed: {e}")
        return False

# Test async LED controller (without hardware)
async def test_async_leds():
    """Test async LED controller"""
    print("\nTesting async LED controller...")
    
    try:
        from lib.async_controllers.async_leds import AsyncNeoPixelController
        
        leds = AsyncNeoPixelController()
        
        # Initialize (will likely fail without hardware, but should handle gracefully)
        await leds.initialize()
        
        # Test LED state updates (should not crash even without hardware)
        await leds.update_wifi_status("connected")
        await leds.update_rocrail_status("connecting")
        await leds.update_direction(True)
        await leds.update_speed_warning(False)
        await leds.update_locomotive_selection(0, 3)
        
        print("✓ Async LED controller test passed (no hardware required)")
        return True
        
    except Exception as e:
        print(f"✗ Async LED test failed: {e}")
        return False

# Main test function
async def run_tests():
    """Run all tests"""
    print("=== Asyncio Controller Component Tests ===")
    
    results = []
    
    # Run tests
    results.append(await test_basic_asyncio())
    results.append(await test_async_state()) 
    results.append(await test_async_leds())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Results: {passed}/{total} passed ===")
    
    if passed == total:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test runner error: {e}")
        sys.exit(1)

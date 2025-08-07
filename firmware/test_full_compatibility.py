"""
Comprehensive MicroPython AsyncIO Compatibility Validation
Run this before starting the full locomotive controller
"""

import asyncio
import time

async def test_all_compatibility():
    """Test all asyncio compatibility fixes"""
    print("=== MicroPython AsyncIO Compatibility Test ===")
    
    # Test 1: Basic asyncio primitives
    print("\n1. Testing basic asyncio primitives...")
    await asyncio.sleep(0.1)
    print("   ✓ asyncio.sleep")
    
    lock = asyncio.Lock()
    async with lock:
        print("   ✓ asyncio.Lock")
        
    event = asyncio.Event()
    event.set()
    assert event.is_set()
    print("   ✓ asyncio.Event")
    
    # Test 2: Task creation and management
    print("\n2. Testing task management...")
    async def test_task():
        await asyncio.sleep(0.1)
        return "success"
    
    task = asyncio.create_task(test_task())
    result = await task
    assert result == "success"
    print("   ✓ asyncio.create_task")
    
    # Test 3: Queue replacement (list + event)
    print("\n3. Testing queue replacement...")
    queue = []
    queue_event = asyncio.Event()
    
    # Simulate queue operations
    queue.append("test_message")
    queue_event.set()
    
    assert len(queue) == 1
    message = queue.pop(0)
    assert message == "test_message"
    queue_event.clear()
    print("   ✓ List + Event queue replacement")
    
    # Test 4: Feature availability check
    print("\n4. Checking asyncio feature availability...")
    features = {
        'wait_for': hasattr(asyncio, 'wait_for'),
        'open_connection': hasattr(asyncio, 'open_connection'),
        'Queue': hasattr(asyncio, 'Queue'),
        'gather': hasattr(asyncio, 'gather'),
        'run': hasattr(asyncio, 'run')
    }
    
    for feature, available in features.items():
        status = "✓" if available else "✗"
        print(f"   {status} asyncio.{feature}")
    
    # Test 5: Time functions compatibility
    print("\n5. Testing time functions...")
    start_time = time.ticks_ms()
    await asyncio.sleep(0.1)
    elapsed = time.ticks_diff(time.ticks_ms(), start_time)
    assert elapsed >= 80  # Allow some timing variance
    print("   ✓ time.ticks_ms and time.ticks_diff")
    
    # Test 6: Stream compatibility simulation
    print("\n6. Testing stream compatibility checks...")
    
    # Simulate connection check without actual connection
    class MockWriter:
        def write(self, data):
            pass
        # Note: no is_closing() method to simulate MicroPython
    
    mock_writer = MockWriter()
    
    # Test our compatibility checks
    connection_valid = (mock_writer is not None and 
                       hasattr(mock_writer, 'write'))
    assert connection_valid
    print("   ✓ Connection validity check (hasattr)")
    
    # Test wait_closed compatibility check
    has_wait_closed = hasattr(mock_writer, 'wait_closed')
    print(f"   ✓ wait_closed availability check: {has_wait_closed}")
    
    print("\n=== All Compatibility Tests Passed! ===")
    print("The asyncio controller should work with your MicroPython version.")
    
    return True

def run_compatibility_test():
    """Run compatibility test with proper error handling"""
    try:
        if hasattr(asyncio, 'run'):
            print("Using asyncio.run()")
            success = asyncio.run(test_all_compatibility())
        else:
            print("Using event loop fallback")
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(test_all_compatibility())
            
        if success:
            print("\n🚀 Ready to run rocrail_controller_asyncio.py")
        
    except Exception as e:
        print(f"\n❌ Compatibility test failed: {e}")
        print("The asyncio controller may not work with your MicroPython version.")
        import sys
        sys.print_exception(e)
        return False
        
    return True

if __name__ == "__main__":
    run_compatibility_test()

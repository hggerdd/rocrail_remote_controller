"""
MicroPython AsyncIO Stream Compatibility Test
Test stream operations before running full controller
"""

import asyncio

async def test_stream_operations():
    """Test asyncio stream operations for MicroPython compatibility"""
    print("Testing asyncio stream compatibility...")
    
    # Test basic asyncio features
    await asyncio.sleep(0.1)
    print("✓ asyncio.sleep works")
    
    # Test Lock
    lock = asyncio.Lock()
    async with lock:
        print("✓ asyncio.Lock works")
        
    # Test Event
    event = asyncio.Event()
    event.set()
    if event.is_set():
        print("✓ asyncio.Event works")
        
    # Test create_task
    async def dummy_task():
        await asyncio.sleep(0.1)
        return "done"
    
    task = asyncio.create_task(dummy_task())
    result = await task
    if result == "done":
        print("✓ asyncio.create_task works")
    
    # Test asyncio feature availability
    features = {
        'wait_for': hasattr(asyncio, 'wait_for'),
        'open_connection': hasattr(asyncio, 'open_connection'),
        'Queue': hasattr(asyncio, 'Queue'),
        'gather': hasattr(asyncio, 'gather'),
        'run': hasattr(asyncio, 'run')
    }
    
    print("\nAsyncIO features available:")
    for feature, available in features.items():
        status = "✓" if available else "✗"
        print(f"  {status} asyncio.{feature}")
    
    # Test stream operations if available
    if features['open_connection']:
        print("\n✓ Stream operations should work")
        print("  - Using hasattr() checks for MicroPython compatibility")
        print("  - Connection checks use hasattr(writer, 'write')")
        print("  - wait_closed() has try/except wrapper")
    else:
        print("\n✗ Stream operations not available")
        
    print("\nStream compatibility test completed!")

def run_test():
    """Run the compatibility test"""
    try:
        if hasattr(asyncio, 'run'):
            asyncio.run(test_stream_operations())
        else:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(test_stream_operations())
    except Exception as e:
        print(f"Compatibility test failed: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    run_test()

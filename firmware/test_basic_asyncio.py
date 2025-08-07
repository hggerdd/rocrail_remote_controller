"""
Simple MicroPython AsyncIO Test
Test basic functionality before running full controller
"""

import asyncio

async def test_basic_asyncio():
    """Test basic asyncio features"""
    print("Testing basic asyncio...")
    
    # Test sleep
    await asyncio.sleep(0.1)
    print("✓ asyncio.sleep works")
    
    # Test Event
    event = asyncio.Event()
    event.set()
    if event.is_set():
        print("✓ asyncio.Event works")
    
    # Test Lock
    lock = asyncio.Lock()
    async with lock:
        print("✓ asyncio.Lock works")
    
    # Test create_task
    async def simple_task():
        await asyncio.sleep(0.1)
        return "task_result"
    
    task = asyncio.create_task(simple_task())
    result = await task
    if result == "task_result":
        print("✓ asyncio.create_task works")
    
    print("Basic asyncio test completed successfully!")

def run_test():
    """Run the test with MicroPython compatibility"""
    try:
        if hasattr(asyncio, 'run'):
            print("Using asyncio.run()")
            asyncio.run(test_basic_asyncio())
        else:
            print("Using event loop fallback")
            loop = asyncio.get_event_loop()
            loop.run_until_complete(test_basic_asyncio())
    except Exception as e:
        print(f"Test failed: {e}")
        import sys
        sys.print_exception(e)

if __name__ == "__main__":
    run_test()

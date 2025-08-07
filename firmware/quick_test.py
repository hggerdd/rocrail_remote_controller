"""
Quick validation test for asyncio controller
"""

import asyncio

async def quick_test():
    """Quick validation test"""
    print("Quick asyncio validation test")
    
    # Test 1: Basic asyncio works
    await asyncio.sleep(0.1)
    print("✓ Basic asyncio.sleep works")
    
    # Test 2: Concurrent tasks
    async def task(name):
        await asyncio.sleep(0.1)
        return f"Task {name} done"
    
    results = await asyncio.gather(task("A"), task("B"))
    print(f"✓ Concurrent tasks: {results}")
    
    # Test 3: Import test
    try:
        from lib.async_controllers.async_state import AsyncControllerState
        state = AsyncControllerState()
        await state.set_wifi_status("test")
        status = await state.get_wifi_status()
        print(f"✓ State management: {status}")
    except Exception as e:
        print(f"✗ State management failed: {e}")
    
    print("Quick test completed")

if __name__ == "__main__":
    asyncio.run(quick_test())

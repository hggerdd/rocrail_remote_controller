"""
Test Connection Recovery for AsyncIO Rocrail Controller
Tests automatic reconnection after WiFi/socket errors
"""

import asyncio
import time

# Mock classes for testing on PC
class MockState:
    def __init__(self):
        self.states = {}
        
    async def set_rocrail_status(self, status):
        self.states['rocrail'] = status
        print(f"[STATE] Rocrail: {status}")
        
    async def get_rocrail_status(self):
        return self.states.get('rocrail', 'disconnected')
        
    async def set_wifi_status(self, status):
        self.states['wifi'] = status
        print(f"[STATE] WiFi: {status}")

class MockLocoList:
    def __init__(self):
        pass
        
    def update_from_rocrail_response(self, data):
        return True

# Import the actual protocol class
import sys
sys.path.append('lib/async_controllers')

# Monkey patch MicroPython specific functions
class MockTime:
    _start = time.time() * 1000
    
    @staticmethod
    def ticks_ms():
        return int((time.time() * 1000) - MockTime._start)
    
    @staticmethod
    def ticks_diff(a, b):
        return a - b

# Replace time module
import lib.async_controllers.async_protocol as protocol_module
protocol_module.time = MockTime

from lib.async_controllers.async_protocol import AsyncRocrailProtocol

async def test_connection_recovery():
    """Test the connection recovery mechanism"""
    print("\n=== Testing Connection Recovery ===\n")
    
    # Create test instances
    loco_list = MockLocoList()
    state = MockState()
    protocol = AsyncRocrailProtocol(loco_list, state)
    
    print("1. Testing error detection in send_task")
    print("-" * 40)
    
    # Simulate a connection
    protocol.host = "test.server"
    protocol.port = 8051
    protocol.writer = type('MockWriter', (), {
        'write': lambda self, data: None,
        'drain': lambda self: asyncio.sleep(0)
    })()
    
    # Queue a message
    protocol._send_queue.append(b"test message")
    protocol._queue_event.set()
    
    # Simulate ENOTCONN error
    async def mock_drain_error():
        raise OSError("[Errno 128] ENOTCONN")
    
    protocol.writer.drain = mock_drain_error
    
    # Create send task
    send_task = asyncio.create_task(protocol._send_task())
    
    # Let it run briefly
    await asyncio.sleep(0.5)
    
    # Check that status was set to lost
    status = await state.get_rocrail_status()
    assert status == "lost", f"Expected 'lost', got '{status}'"
    print("✓ ENOTCONN error detected and status set to 'lost'")
    
    # Check that reconnect task was started
    assert protocol.reconnect_task is not None, "Reconnect task not started"
    print("✓ Auto-reconnect task started")
    
    send_task.cancel()
    try:
        await send_task
    except asyncio.CancelledError:
        pass
    
    print("\n2. Testing auto-reconnect with backoff")
    print("-" * 40)
    
    # Reset state
    await state.set_rocrail_status("lost")
    protocol.writer = None
    protocol.reader = None
    
    # Mock connect method to fail first 2 times, then succeed
    connect_attempts = 0
    original_connect = protocol.connect
    
    async def mock_connect(host, port, timeout=10):
        nonlocal connect_attempts
        connect_attempts += 1
        print(f"  Connect attempt {connect_attempts}")
        if connect_attempts < 3:
            print(f"  → Failed (simulated)")
            return False
        else:
            print(f"  → Success (simulated)")
            protocol.writer = type('MockWriter', (), {'write': lambda s, d: None})()
            protocol.reader = type('MockReader', (), {})()
            await state.set_rocrail_status("connected")
            return True
    
    protocol.connect = mock_connect
    
    # Start auto-reconnect
    reconnect_task = asyncio.create_task(protocol._auto_reconnect())
    
    # Wait for reconnection to complete
    await asyncio.sleep(10)  # Should take ~8 seconds (1s + 2s + 5s delays)
    
    assert connect_attempts == 3, f"Expected 3 connect attempts, got {connect_attempts}"
    print("✓ Exponential backoff working (3 attempts with delays)")
    
    status = await state.get_rocrail_status()
    assert status == "connected", f"Expected 'connected', got '{status}'"
    print("✓ Successfully reconnected after failures")
    
    reconnect_task.cancel()
    try:
        await reconnect_task
    except asyncio.CancelledError:
        pass
    
    print("\n3. Testing receive task error handling")
    print("-" * 40)
    
    # Reset state
    await state.set_rocrail_status("connected")
    protocol.reader = type('MockReader', (), {})()
    
    # Simulate connection closed by server
    async def mock_read(size):
        return b""  # Empty data means server closed connection
    
    protocol.reader.read = mock_read
    
    # Create receive task
    receive_task = asyncio.create_task(protocol._receive_task())
    
    # Let it run briefly
    await asyncio.sleep(0.5)
    
    # Check that status was set to lost
    status = await state.get_rocrail_status()
    assert status == "lost", f"Expected 'lost' after server disconnect, got '{status}'"
    print("✓ Server disconnect detected")
    
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass
    
    print("\n=== All Connection Recovery Tests Passed ===\n")

async def main():
    """Run all tests"""
    try:
        await test_connection_recovery()
        print("\n✅ ALL TESTS PASSED")
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run with Python's asyncio
    asyncio.run(main())

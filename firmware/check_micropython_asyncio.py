"""
MicroPython AsyncIO Compatibility Test
Check which asyncio features are available
"""

def check_asyncio_compatibility():
    """Check what asyncio features are available"""
    
    try:
        import asyncio
        print("✓ asyncio module available")
    except ImportError:
        print("✗ asyncio module not available")
        return
        
    # Check basic asyncio features
    features = {
        'sleep': hasattr(asyncio, 'sleep'),
        'Event': hasattr(asyncio, 'Event'), 
        'Lock': hasattr(asyncio, 'Lock'),
        'Queue': hasattr(asyncio, 'Queue'),
        'create_task': hasattr(asyncio, 'create_task'),
        'gather': hasattr(asyncio, 'gather'),
        'wait_for': hasattr(asyncio, 'wait_for'),
        'open_connection': hasattr(asyncio, 'open_connection'),
        'run': hasattr(asyncio, 'run')
    }
    
    print("\nAsyncIO Feature Availability:")
    for feature, available in features.items():
        status = "✓" if available else "✗"
        print(f"{status} asyncio.{feature}")
        
    # Check for MicroPython specific limitations
    print(f"\nMicroPython compatibility notes:")
    if not features['Queue']:
        print("- asyncio.Queue not available → use list + Event")
    if not features['gather']:
        print("- asyncio.gather limited → use create_task + await")
    if not features['run']:
        print("- asyncio.run may not exist → use get_event_loop()")
        
    return features

if __name__ == "__main__":
    check_asyncio_compatibility()

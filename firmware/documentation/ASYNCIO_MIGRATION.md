# AsyncIO Migration Guide

## Switching from Legacy to AsyncIO Implementation

### File Changes Required

1. **Main Controller:**
   - Replace `rocrail_controller.py` with `rocrail_controller_asyncio.py`
   - Or rename: `mv rocrail_controller.py rocrail_controller_legacy.py`
   - Then: `mv rocrail_controller_asyncio.py rocrail_controller.py`

2. **Boot Configuration:**
   - Update `boot.py` if it references specific controller files
   - Ensure asyncio is available in MicroPython build

3. **Dependencies:**
   - All existing lib/ modules remain compatible
   - New async_controllers/ directory contains asyncio components
   - No changes needed to: config.py, hardware_config.py, loco_list.py

### Behavioral Differences

**Timing:**
- AsyncIO uses precise async timing instead of polling intervals
- LED updates may appear smoother and more responsive
- Memory usage is more predictable with structured cleanup

**State Management:**
- No global variables - all state managed by async primitives
- Better isolation between components
- Automatic cleanup on shutdown/error

**Error Handling:**
- More robust error recovery with proper async exception handling
- Tasks can be individually restarted if needed
- Better resource cleanup on connection failures

### Performance Improvements

**Memory:**
- Lower memory overhead (no thread stacks)
- Better garbage collection with structured cleanup
- Predictable memory usage patterns

**CPU:**
- Single event loop instead of multiple threads
- Better CPU utilization with cooperative multitasking
- Reduced context switching overhead

**Responsiveness:**
- Event-driven button handling (no polling delay)
- Immediate response to hardware inputs
- Better WiFi/RocRail connection handling

### Testing the Migration

1. **Component Testing:**
   ```python
   python test_asyncio.py
   python quick_test.py
   ```

2. **Hardware Testing:**
   - Test all buttons and potentiometer
   - Verify LED status indicators work correctly
   - Check WiFi reconnection behavior
   - Validate RocRail communication

3. **Rollback Plan:**
   - Keep legacy `rocrail_controller_legacy.py` as backup
   - Can switch back by renaming files
   - All configuration and locomotive data preserved

### Configuration Adjustments

**Optional LED Tuning:**
- See `LED_RECOMMENDATIONS.py` for suggested brightness adjustments
- AsyncIO may require different blink intervals for optimal visibility
- Test with actual hardware to find preferred settings

**Memory Monitoring:**
- AsyncIO implementation includes enhanced memory monitoring
- Consider adjusting cleanup intervals in config.py if needed
- Monitor free memory during extended operation

### Troubleshooting

**Common Issues:**
1. **Import Errors:** Ensure all async_controllers/ modules are present
2. **Timing Issues:** Check that config intervals are in milliseconds
3. **LED Problems:** Verify NeoPixel hardware compatibility
4. **Connection Issues:** Test WiFi/RocRail connectivity separately

**Debug Tools:**
- Enhanced logging in asyncio implementation
- Task monitoring and status reporting
- Memory usage tracking and alerts

# MicroPython AsyncIO Compatibility Checklist

Use this checklist when implementing asyncio code for MicroPython to avoid common failures.

## ✅ Pre-Implementation Checklist

### AsyncIO Feature Availability
- [ ] Check if `asyncio.Queue` is available → Use `list + asyncio.Event` if not
- [ ] Check if `asyncio.wait_for` is available → Add fallback if not  
- [ ] Check if `asyncio.gather` works reliably → Use individual task monitoring
- [ ] Check if `asyncio.run` exists → Add `get_event_loop().run_until_complete()` fallback

### Stream Operations
- [ ] Use `hasattr(writer, 'write')` instead of `writer.is_closing()`
- [ ] Wrap `writer.wait_closed()` with `hasattr()` check
- [ ] Handle stream errors gracefully with try/except
- [ ] Test actual socket connections, not just mock objects

### Hardware Integration
- [ ] Migrate ALL hardware calibration values (potentiometer ranges, LED brightness, etc.)
- [ ] Don't assume linear mappings work - check mechanical constraints
- [ ] Simplify button debouncing - avoid complex boolean logic
- [ ] Test hardware timing with actual MicroPython timing functions

### Time Functions
- [ ] Use `time.ticks_ms()` and `time.ticks_diff()` instead of `time.time()`
- [ ] Handle overflow in tick calculations properly
- [ ] Test timing accuracy on actual hardware

## 🧪 Testing Protocol

### 1. Basic Compatibility Test
```bash
python test_basic_asyncio.py
```
- [ ] Basic asyncio primitives work
- [ ] Task creation and management
- [ ] Event and Lock functionality

### 2. Stream Compatibility Test  
```bash
python test_stream_compatibility.py
```
- [ ] Stream operations don't crash
- [ ] Connection checking works
- [ ] Proper error handling

### 3. Hardware Functionality Test
```bash
python test_buttons_asyncio.py        # Buttons
python test_poti_calibration.py       # Potentiometer  
```
- [ ] All buttons respond correctly
- [ ] Potentiometer covers full range (0-100)
- [ ] Hardware calibration is accurate

### 4. Complete System Test
```bash
python test_full_compatibility.py
```
- [ ] All asyncio features work together
- [ ] No compatibility errors
- [ ] System ready for deployment

## 🚨 Common Error Patterns to Avoid

### 1. Queue Usage
```python
# ❌ Will fail in MicroPython
queue = asyncio.Queue()
await queue.put(item)
item = await queue.get()

# ✅ MicroPython compatible
queue = []
queue_event = asyncio.Event()

# Producer
queue.append(item)
queue_event.set()

# Consumer
await queue_event.wait()
if queue:
    item = queue.pop(0)
    if not queue:
        queue_event.clear()
```

### 2. Stream Connection Checking
```python
# ❌ Will fail: 'Stream' object has no attribute 'is_closing'
if writer and not writer.is_closing():

# ✅ MicroPython compatible
if writer and hasattr(writer, 'write'):
```

### 3. Button Debouncing
```python
# ❌ Complex logic prone to errors
if current_state != (not self._button_states[name]):
    # Multiple negations = confusion

# ✅ Simple and clear
if last_state == 1 and current_state == 0:
    return True  # Button pressed (pull-up logic)
```

### 4. Event Loop Management
```python
# ❌ May not exist in older MicroPython
asyncio.run(main())

# ✅ Compatible approach
if hasattr(asyncio, 'run'):
    asyncio.run(main())
else:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```

## 📋 Deployment Verification

Before considering asyncio implementation complete:

- [ ] All compatibility tests pass
- [ ] Hardware responds correctly to all inputs
- [ ] No asyncio-related error messages in logs
- [ ] Performance is acceptable (memory usage, responsiveness)
- [ ] System recovers gracefully from connection failures
- [ ] All features work identically to legacy implementation

## 🔄 Troubleshooting Quick Reference

**Error: "Queue"** → Replace asyncio.Queue with list + Event
**Error: "'Stream' object has no attribute..."** → Add hasattr() checks  
**Error: "Buttons not working"** → Simplify debouncing logic
**Error: "Limited potentiometer range"** → Add hardware calibration
**Error: "asyncio.run not found"** → Add event loop fallback

This checklist captures all the issues discovered during the locomotive controller asyncio migration.

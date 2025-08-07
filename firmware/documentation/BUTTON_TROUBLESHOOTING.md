# Button Troubleshooting Guide - AsyncIO Implementation

## Issue: Buttons Not Working

The asyncio implementation had non-functional buttons due to complex debouncing logic. This has been fixed.

## Quick Fix Test

**1. Test Raw Button Hardware:**
```bash
python test_raw_buttons.py
```
- Shows raw pin values (1=not pressed, 0=pressed) 
- Verifies hardware wiring is correct
- Should show state changes when buttons are pressed

**2. Test AsyncIO Hardware Manager:**
```bash
python test_minimal_buttons.py
```
- Tests the fixed AsyncHardwareManager
- Should show "[BUTTON] button_name press detected!" messages
- Verifies the button reading logic works

**3. Test Full Button Functionality:**
```bash
python test_buttons_asyncio.py
```
- Complete button test with locomotive controller integration
- Shows all button presses with descriptive names
- Tests potentiometer as well

## What Was Fixed

### Original Problem
- Complex debouncing logic with multiple negations
- State tracking errors preventing button detection
- 50ms debounce time too slow for good responsiveness

### Solution Applied
```python
# New simplified button logic:
if self._last_button_states[name] == 1 and current_value == 0:
    # Button pressed (1→0 transition for pull-up)
    return True
```

### Key Changes
1. **Simplified Logic**: Direct 1→0 transition detection
2. **Reduced Debounce**: 50ms → 20ms for responsiveness  
3. **Debug Output**: "[BUTTON] name press detected!" messages
4. **Proper State Init**: Uses actual pin values, not assumptions

## Hardware Verification

**Button Pin Mapping:**
- Emergency (red): Pin 17
- Direction (green): Pin 19  
- Sound (yellow): Pin 22
- Light (blue): Pin 23
- Up (black): Pin 18
- Down (black): Pin 21

**Expected Behavior:**
- Pull-up resistors: Pin reads 1 when not pressed, 0 when pressed
- Debounce time: 20ms
- Should trigger on button press (not release)

## Rollback Plan

If buttons still don't work:

**1. Check Hardware:**
```bash
python test_raw_buttons.py
```
If raw pins don't change, check physical wiring.

**2. Use Legacy Controller:**
```bash
python rocrail_controller.py  # (original working version)
```

**3. Compare Button Logic:**
The working legacy button logic is in `lib/button_controller.py` for reference.

## Debugging Output

When buttons work correctly, you should see:
```
[BUTTON] emergency press detected!
⚠STOP!

[BUTTON] direction press detected!  
Direction: t

[BUTTON] light press detected!
Light: t
```

If you see the "[BUTTON]" debug messages but not the action messages, the issue is in the main controller logic, not the hardware manager.

## Next Steps

After confirming buttons work with the test scripts:
1. Run the full controller: `python rocrail_controller_asyncio.py`
2. The debug messages will help verify button detection
3. Remove debug output by commenting the print statement in `_read_button_debounced()` once confirmed working

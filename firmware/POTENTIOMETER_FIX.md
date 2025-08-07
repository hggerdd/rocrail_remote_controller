# Potentiometer Calibration Fix - AsyncIO Implementation

## Issue
The AsyncIO hardware controller was missing the potentiometer calibration that accounts for mechanical limitations of the physical potentiometer.

## Problem Details
- **Physical constraint**: Potentiometer cannot reach full ADC range (0-4095)
- **Actual range**: Only 1310-2360 usable due to mechanical stops
- **Missing mapping**: AsyncIO implementation used simple linear 0-4095 → 0-100 mapping
- **Result**: Only partial speed control, inconsistent with legacy controller

## Solution Applied

### 1. Added Calibration Constants
```python
self.POTI_MIN_VALUE = 1310  # Minimum mechanical poti value
self.POTI_MAX_VALUE = 2360  # Maximum mechanical poti value
```

### 2. Implemented Normalization Method
```python
def _normalize_speed(self, raw_value):
    if raw_value <= self.POTI_MIN_VALUE:
        normalized = 0
    elif raw_value >= self.POTI_MAX_VALUE:
        normalized = 100  # Maximum locomotive speed
    else:
        ratio = (raw_value - self.POTI_MIN_VALUE) / (self.POTI_MAX_VALUE - self.POTI_MIN_VALUE)
        normalized = int(ratio * 100)
    return max(0, min(100, normalized))
```

### 3. Updated Speed Reading
- Raw ADC values now normalized before filtering
- Maintains smooth speed control across full mechanical range
- Consistent behavior with legacy controller

## Testing the Fix

### Quick Test
```bash
python test_poti_calibration.py
```

### Expected Output
```
Raw ADC | Normalized | Status
-------|------------|--------
   1310 |         0  | In range (minimum)
   1835 |        50  | In range (middle)
   2360 |       100  | In range (maximum)
```

### Integration Test
```bash
python test_buttons_asyncio.py
```
Now shows: `🎛️ Speed: 50 (Raw: 1835, Range: 1310-2360)`

## Verification Points

✅ **Minimum Position**: Raw ~1310 → Speed 0  
✅ **Maximum Position**: Raw ~2360 → Speed 100  
✅ **Mid Position**: Raw ~1835 → Speed ~50  
✅ **Below Range**: Raw <1310 → Speed 0 (clamped)  
✅ **Above Range**: Raw >2360 → Speed 100 (clamped)  

## Files Updated

- ✅ `lib/async_controllers/async_hardware.py` - Added calibration logic
- ✅ `test_poti_calibration.py` - Real-time calibration testing
- ✅ `test_buttons_asyncio.py` - Shows raw ADC values for debugging
- ✅ `README_DEVELOPMENT.md` - Documented potentiometer calibration

## Rollback Plan

If calibration causes issues:

1. **Adjust calibration values** in `async_hardware.py`:
   ```python
   self.POTI_MIN_VALUE = YOUR_MIN_VALUE
   self.POTI_MAX_VALUE = YOUR_MAX_VALUE  
   ```

2. **Find your values** using:
   ```bash
   python test_poti_calibration.py  # Choose option 2
   ```

3. **Disable calibration** (temporary):
   ```python
   def _normalize_speed(self, raw_value):
       return int((raw_value / 4095.0) * 100)  # Simple linear mapping
   ```

The potentiometer should now provide smooth speed control across its full mechanical range! 🎛️

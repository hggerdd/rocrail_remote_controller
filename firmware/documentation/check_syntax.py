"""
Quick syntax check for connection recovery changes
"""

# Check that the updated files have correct Python syntax
import ast
import os

files_to_check = [
    "lib/async_controllers/async_protocol.py",
    "lib/async_controllers/async_leds.py",
    "rocrail_controller_asyncio.py"
]

print("Checking Python syntax of updated files...")
print("-" * 50)

all_good = True
for filepath in files_to_check:
    try:
        with open(filepath, 'r') as f:
            code = f.read()
        ast.parse(code)
        print(f"✓ {filepath}: Syntax OK")
    except SyntaxError as e:
        print(f"✗ {filepath}: Syntax Error at line {e.lineno}: {e.msg}")
        all_good = False
    except Exception as e:
        print(f"✗ {filepath}: Error: {e}")
        all_good = False

print("-" * 50)
if all_good:
    print("✅ All files have valid Python syntax")
    print("\nKey improvements added:")
    print("1. Auto-reconnection with exponential backoff")
    print("2. ENOTCONN error detection and handling")
    print("3. Improved LED feedback for connection states")
    print("4. Prevents duplicate reconnection attempts")
else:
    print("❌ Some files have syntax errors")

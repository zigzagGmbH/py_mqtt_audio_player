# check_version.py
import sounddevice as sd
import sys

print(f"Sounddevice version: {sd.__version__}")
print(f"Python version: {sys.version}")

# Check available attributes
print("\nAvailable default attributes:")
for attr in dir(sd.default):
    if not attr.startswith('_'):
        print(f"  - {attr}")

# Check if we can use exclusive parameter in OutputStream
import inspect
print("\nOutputStream parameters:")
sig = inspect.signature(sd.OutputStream)
for param in sig.parameters:
    print(f"  - {param}")
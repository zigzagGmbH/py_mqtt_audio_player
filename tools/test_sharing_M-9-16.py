# test_sharing.py
import sounddevice as sd
import time

print("=" * 80)
print("TESTING DEVICE SHARING CAPABILITY")
print("=" * 80)

# Your MADI (9-16) devices from different APIs
devices_to_test = [
    {'id': 12, 'name': 'MADI (9-16) via MME', 'api': 'MME'},
    {'id': 28, 'name': 'MADI (9-16) via DirectSound', 'api': 'DirectSound'},
    {'id': 35, 'name': 'MADI (9-16) via WASAPI', 'api': 'WASAPI'},
    {'id': 50, 'name': 'MADI (9-16) via WDM-KS', 'api': 'WDM-KS'},
]

print("\nTesting each device for multi-instance capability...")
print("-" * 80)

for device in devices_to_test:
    print(f"\nTesting Device {device['id']}: {device['name']}")
    print(f"Host API: {device['api']}")
    
    try:
        # Try to open first stream
        print("  Opening first stream...", end="")
        stream1 = sd.OutputStream(
            device=device['id'],
            channels=8,
            samplerate=44100,
            blocksize=2048,
            latency='high'
        )
        stream1.start()
        print(" SUCCESS")
        
        # Try to open second stream on same device
        print("  Opening second stream...", end="")
        stream2 = sd.OutputStream(
            device=device['id'],
            channels=8,
            samplerate=44100,
            blocksize=2048,
            latency='high'
        )
        stream2.start()
        print(" SUCCESS")
        
        print(f"  ✓ Device {device['id']} ({device['api']}) SUPPORTS SHARING!")
        
        # Clean up
        stream1.stop()
        stream2.stop()
        stream1.close()
        stream2.close()
        
    except Exception as e:
        print(f" FAILED")
        print(f"  ✗ Device {device['id']} ({device['api']}) does NOT support sharing")
        print(f"    Error: {str(e)[:100]}")
        
        # Clean up first stream if it was opened
        try:
            stream1.stop()
            stream1.close()
        except:
            pass

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("-" * 80)
print("Use one of the devices marked with ✓ for multi-instance support")
print("Update your config to use the working device ID instead of 50")
import sounddevice as sd

def diagnose_audio_devices():
    """Diagnose all audio devices and their host APIs"""
    
    print("=" * 80)
    print("AUDIO SYSTEM DIAGNOSTIC")
    print("=" * 80)
    
    # 1. List all Host APIs
    print("\n1. AVAILABLE HOST APIs:")
    print("-" * 40)
    hostapis = sd.query_hostapis()
    for i, api in enumerate(hostapis):
        print(f"  API {i}: {api['name']}")
        print(f"    - Default Input Device: {api['default_input_device']}")
        print(f"    - Default Output Device: {api['default_output_device']}")
        print(f"    - Device Count: {api['devices']}")
    
    # 2. List all devices with their Host API
    print("\n2. ALL AUDIO DEVICES BY HOST API:")
    print("-" * 40)
    devices = sd.query_devices()
    
    # Group devices by Host API
    devices_by_api = {}
    for i, device in enumerate(devices):
        api_index = device['hostapi']
        api_name = hostapis[api_index]['name']
        
        if api_name not in devices_by_api:
            devices_by_api[api_name] = []
        
        devices_by_api[api_name].append({
            'index': i,
            'name': device['name'],
            'channels': device['max_output_channels'],
            'sample_rate': device['default_samplerate']
        })
    
    # Print devices grouped by API
    for api_name, api_devices in devices_by_api.items():
        print(f"\n{api_name}:")
        for dev in api_devices:
            if dev['channels'] > 0:  # Only show output devices
                print(f"  Device {dev['index']}: {dev['name']}")
                print(f"    - Channels: {dev['channels']} out")
                print(f"    - Sample Rate: {dev['sample_rate']} Hz")
    
    # 3. Find your MADI devices specifically
    print("\n3. MADI DEVICES ANALYSIS:")
    print("-" * 40)
    madi_devices = []
    for i, device in enumerate(devices):
        if 'MADI' in device['name'] and device['max_output_channels'] > 0:
            api_name = hostapis[device['hostapi']]['name']
            madi_devices.append({
                'index': i,
                'name': device['name'],
                'api': api_name,
                'channels': device['max_output_channels']
            })
            print(f"  Device {i}: {device['name']}")
            print(f"    HOST API: {api_name}")
            print(f"    Channels: {device['max_output_channels']}")
    
    # 4. Test latency modes (since exclusive parameter isn't available)
    print("\n4. TESTING LATENCY MODES FOR SHARING:")
    print("-" * 40)
    
    # Find MADI (9-16) device
    target_device = None
    for i, device in enumerate(devices):
        if 'MADI (9-16)' in device['name'] and 'MADIface' in device['name']:
            target_device = i
            print(f"Testing device {i}: {device['name']}")
            break
    
    if target_device is not None:
        # Test with high latency (better for sharing)
        try:
            stream = sd.OutputStream(device=target_device, latency='high')
            stream.close()
            print("  ✓ High latency mode: SUPPORTED")
        except Exception as e:
            print(f"  ✗ High latency mode: FAILED - {e}")
        
        # Test with specific latency value
        try:
            stream = sd.OutputStream(device=target_device, latency=0.1)
            stream.close()
            print("  ✓ 100ms latency: SUPPORTED")
        except Exception as e:
            print(f"  ✗ 100ms latency: FAILED - {e}")
    
    return madi_devices

if __name__ == "__main__":
    # Set high latency for better sharing (since exclusive mode isn't available)
    sd.default.latency = 'high'
    
    # Run diagnostic
    madi_devices = diagnose_audio_devices()
    
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS:")
    print("-" * 40)
    
    # Check if we found ASIO devices
    asio_found = False
    wasapi_found = False
    for dev in madi_devices:
        if 'ASIO' in dev['api']:
            asio_found = True
        if 'WASAPI' in dev['api']:
            wasapi_found = True
    
    if asio_found:
        print("• ASIO devices detected - these typically use exclusive mode")
        print("  Solution: Use high latency mode with sd.default.latency = 'high'")
        print("  Or use different MADI channel groups for each instance")
    
    if wasapi_found:
        print("• WASAPI devices detected - these can use shared or exclusive mode")
        print("  Solution: Use high latency mode for better sharing")
    
    print("\n• To use WASAPI devices specifically, filter by Host API")
    print("• Consider using different MADI channel groups for different instances")
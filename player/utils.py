"""
Audio utilities for device discovery and file management.
"""

import os
import glob
import sounddevice as sd
from colorama import Fore, Style


def find_device_by_name(device_name):
    """Find a device by its name and return its index, preferring output devices."""
    devices = sd.query_devices()

    # First pass: exact match among OUTPUT devices only
    for device in devices:
        if device["name"] == device_name and device["max_output_channels"] > 0:
            return device["index"]  # ← Correct device index

    # Fallback
    for device in devices:
        if device["name"] == device_name:
            return device["index"]

    return None


def list_available_devices():
    """List all available audio output devices with details."""
    devices = sd.query_devices()
    output_devices = []

    print(f"\n{Fore.CYAN}Available Audio Output Devices:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}" + "-" * 50 + f"{Style.RESET_ALL}")

    for i, device in enumerate(devices):
        # Only consider output devices
        if device["max_output_channels"] > 0:
            is_default = i == sd.default.device[1]
            default_marker = (
                f" {Fore.GREEN}(DEFAULT){Style.RESET_ALL}" if is_default else ""
            )

            print(
                f"{Fore.YELLOW}Device {i}: {device['name']}{default_marker}{Style.RESET_ALL}"
            )
            print(f"  Channels: {device['max_output_channels']} out")
            print(f"  Sample Rate: {device['default_samplerate']} Hz")
            print(
                f"  Device type: {'Input' if device['max_input_channels'] > 0 else ''}"
                f"{' & ' if device['max_input_channels'] > 0 and device['max_output_channels'] > 0 else ''}"
                f"{'Output' if device['max_output_channels'] > 0 else ''}"
            )
            output_devices.append(i)

    print(f"{Fore.CYAN}" + "-" * 50 + f"{Style.RESET_ALL}")
    return output_devices


def confirm_selected_device(device=None, target_channels=2, channel_mapping=None):
    """Validate and configure a sound device for audio playback."""
    device_index = None
    device_info = None

    # Default channel mapping if needed
    if channel_mapping is None:
        channel_mapping = [1] * target_channels

    # ** Get device index & convert to name, if necessary
    if device is None:
        device_index = sd.default.device[1]
    elif isinstance(device, str):
        device_index = find_device_by_name(device)
        if device_index is None:
            print(f"Device '{device}' not found. Using default.")
            device_index = sd.default.device[1]
    else:
        device_index = device

    # Validate device exists and is an output device
    all_devices = sd.query_devices()
    if device_index >= len(all_devices):
        print(f"Device index {device_index} out of range. Using default.")
        device_index = sd.default.device[1]
    elif all_devices[device_index]["max_output_channels"] == 0:
        print(f"Device {device_index} is not an output device. Using default.")
        device_index = sd.default.device[1]

    # Get device info
    device_info = sd.query_devices(device_index)

    # Check channel compatibility
    available_channels = device_info["max_output_channels"]
    if available_channels < target_channels:
        print(
            f"Device only supports {available_channels} channels, but {target_channels} requested."
        )
        print(f"Adjusting to {available_channels} channels.")
        target_channels = available_channels
        if len(channel_mapping) > target_channels:
            channel_mapping = channel_mapping[:target_channels]
            print(f"Channel mapping truncated to: {channel_mapping}")

    return device_info, device_index, target_channels, channel_mapping


def is_valid_audio_file(filepath):
    """Check if a file is a valid audio file (not a macOS metadata file)."""
    filename = os.path.basename(filepath)

    # Filter out macOS metadata files and other system files
    if filename.startswith("._"):
        return False
    if filename.startswith(".DS_Store"):
        return False
    if filename.startswith("Thumbs.db"):  # Windows thumbnail cache
        return False

    # Check file size (metadata files are usually very small)
    try:
        file_size = os.path.getsize(filepath)
        if file_size < 1000:  # Less than 1KB is likely not a real audio file
            return False
    except OSError:
        return False

    return True


def find_audio_files(input_dir):
    """Find available audio files in the specified directory."""
    wav_files = None
    audio_file_exists = False
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    input_audio_file_dir = os.path.join(parent_dir, input_dir)

    if os.path.exists(input_audio_file_dir):
        print(
            f"{Fore.LIGHTGREEN_EX}Input directory exists:{Style.RESET_ALL} {input_audio_file_dir}"
        )
        # Get all .wav files
        all_wav_files = glob.glob(os.path.join(input_audio_file_dir, "*.wav"))

        # Filter out invalid files (macOS metadata, etc.)
        wav_files = [f for f in all_wav_files if is_valid_audio_file(f)]

        if wav_files:
            audio_file_exists = True
            print(f'{Fore.LIGHTGREEN_EX}".wav" file present{Style.RESET_ALL}')
            print(f"Found {len(wav_files)} valid .wav file(s):")
            for wav_file in wav_files:
                print(f"  - {os.path.basename(wav_file)}")

            # If we filtered out files, show what was ignored
            ignored_files = [f for f in all_wav_files if not is_valid_audio_file(f)]
            if ignored_files:
                print(
                    f"{Fore.YELLOW}Ignored {len(ignored_files)} invalid file(s):{Style.RESET_ALL}"
                )
                for ignored_file in ignored_files:
                    print(
                        f"  - {os.path.basename(ignored_file)} (metadata/system file)"
                    )
    else:
        os.makedirs(input_audio_file_dir, exist_ok=True)
        print(
            f"{Fore.LIGHTYELLOW_EX}Creating input directory:{Style.RESET_ALL} {input_audio_file_dir}"
        )

    if not audio_file_exists:
        print(
            f"{Fore.LIGHTYELLOW_EX}Warning:{Style.RESET_ALL} No valid .wav files found in the directory!"
        )
        print(
            'Please place an audio file of .wav type in the "audio/" dir and try again!'
        )
        return None, False, input_audio_file_dir

    return wav_files, audio_file_exists, input_audio_file_dir
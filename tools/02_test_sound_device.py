"""
- CONFIGURING SOUND DEVICE:
    - external args allow to launch in interactive

- PLAYING SOUND FILE:
    - Transform audio data (.wav) for sound card output channel and audio level & sample rate and keep it in memory
    - Play from memory (using sound device's kernel specific stream api)
    - Play through a specific channel of sound card with target remapping of sample rate and other features ...
    - Save to disk, for logging and review purposes
"""

# -------------- #
# -- Util Libs --#
# -------------- #
import os
import sys
from pathlib import Path
import yaml
from jinja2 import Template
from colorama import Fore, Style

# ----------------------------- #
# -- Main playback ctrl libs -- #
# ----------------------------- #
import numpy as np
from scipy import signal
import soundfile as sf
import sounddevice as sd

# ----------------- #
# -- Load config -- #
# ----------------- #
# Get the script's directory and go one level up to project root to get config.yml first
script_dir = Path(__file__).parent
project_root = script_dir.parent
config_path = project_root / "config.yaml"

with open(config_path, "r") as file:
    config_str = file.read()

config_unrendered = yaml.safe_load(config_str)

logging_config = config_unrendered["logging"]
paths_config = config_unrendered["paths"]
player_config = config_unrendered["player"]

# Use Jinja2 to process the template for MQTT info
mqtt_template = Template(config_str)
rendered_mqtt_info = mqtt_template.render(mqtt=config_unrendered["mqtt"])
mqtt_config = yaml.safe_load(rendered_mqtt_info)


# --------------------------- #
# -- Playback ctrl vectors -- #
# --------------------------- #

# 1. Use system default
# TARGET_SOUND_DEVICE = None
# 2. or set target global device by index
# TARGET_SOUND_DEVICE = 1  # Use the device with index 1
# 3. OR set by name (full or partial match)
# TARGET_SOUND_DEVICE = "MacBook Pro Speakers"
# TARGET_SOUND_DEVICE = "VBMatrix In 2 (VB-Audio Matrix VAIO)"
# TARGET_SOUND_DEVICE = "External Headphones"
TARGET_SOUND_DEVICE = player_config["device_name"]

# TARGET_SAMPLE_RATE = 48000
TARGET_SAMPLE_RATE = player_config["device_sample_rate"]
# TARGET_VOLUME_FACTOR = 1
TARGET_VOLUME_FACTOR = player_config["playback_volume_factor"]
# TARGET_TOTAL_CHANNELS = 2
TARGET_TOTAL_CHANNELS = player_config["device_channels"]
# TARGET_CHANNEL_MASK = [0, 1]  # Default: enable both 1 channel
TARGET_CHANNEL_MASK = player_config["playback_channel_mask"]

# --> Audio file path stuff <-- #
# AUDIO_DIR = "audio"
AUDIO_DIR = paths_config["audio_file_dir"]
# Get the script's directory and go one level up to project root
# script_dir = Path(__file__).parent
# project_root = script_dir.parent
# Create the full input path to audio directory at project root
INPUT_AUDIO_FILE_DIR = project_root / AUDIO_DIR


def is_valid_audio_file(filepath):
    """Check if a file is a valid audio file (not a macOS metadata file)."""
    filename = os.path.basename(str(filepath))

    # Filter out macOS metadata files and other system files
    if filename.startswith("._"):
        return False
    if filename.startswith(".DS_Store"):
        return False
    if filename.startswith("Thumbs.db"):  # Windows thumbnail cache
        return False

    # Check file size (metadata files are usually very small)
    try:
        file_size = (
            filepath.stat().st_size
            if isinstance(filepath, Path)
            else os.path.getsize(filepath)
        )
        if file_size < 1000:  # Less than 1KB is likely not a real audio file
            return False
    except OSError:
        return False

    return True


# Check if directory exists and create if necessary
# Then check if .wav file is present in that dir ...
wav_files = None
audio_file_exists = False
# if os.path.exists(INPUT_AUDIO_FILE_DIR):
if INPUT_AUDIO_FILE_DIR.exists():
    print()
    print(
        f"{Fore.LIGHTGREEN_EX}Input directory exists:{Style.RESET_ALL} {INPUT_AUDIO_FILE_DIR}"
    )
    # Check for .wav files in the directory
    all_wav_files = list(INPUT_AUDIO_FILE_DIR.glob("*.wav"))

    # Filter out invalid files (macOS metadata, etc.)
    valid_wav_files = [f for f in all_wav_files if is_valid_audio_file(f)]

    # Convert Path objects to strings if needed for compatibility
    wav_files = [str(f) for f in valid_wav_files]

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
                    f"  - {os.path.basename(str(ignored_file))} (metadata/system file)"
                )
else:
    # os.makedirs(INPUT_AUDIO_FILE_DIR, exist_ok=True)
    INPUT_AUDIO_FILE_DIR.mkdir(parents=True, exist_ok=True)
    print(
        f"{Fore.LIGHTYELLOW_EX}Creating input directory:{Style.RESET_ALL} {INPUT_AUDIO_FILE_DIR}"
    )

if not audio_file_exists:
    print(
        f"{Fore.LIGHTYELLOW_EX}Warning:{Style.RESET_ALL} No valid .wav files found in the directory!"
    )
    print('Please place an audio file of .wav type in the "audio/" dir and try again!')
    print()
    sys.exit(0)


def load_audio_file(audio_file):
    print(
        f"{Fore.LIGHTCYAN_EX}Loading audio file:{Style.RESET_ALL} {os.path.basename(audio_file)}"
    )

    try:
        # Load audio data and get original sample rate
        audio_data_array, orig_sample_rate = sf.read(audio_file)

        print(f"  • Original sample rate: {orig_sample_rate} Hz")
        print(
            f"  • Audio duration: {len(audio_data_array) / orig_sample_rate:.2f} seconds"
        )
        print(f"  • Audio shape: {audio_data_array.shape}")

        # Convert to mono if stereo
        if len(audio_data_array.shape) > 1:
            audio_data_array = np.mean(audio_data_array, axis=1)
            print("  • Converted to mono")
        return audio_data_array, orig_sample_rate
    except Exception as e:
        print(f"{Fore.RED}Error loading audio file:{Style.RESET_ALL} {e}")
        sys.exit(1)


# [Utility] - Gain ctrl - Method 1
# Simple linear volume control (0.0 to 1.0)
def adjust_volume_linear(audio_data, volume_factor):
    """
    Adjust volume using a simple linear scaling factor.

    Args:
        audio_data: Audio samples as numpy array
        volume_factor: Scale from 0.0 (silent) to 1.0 (original volume)
                       Can go above 1.0 but may cause clipping

    Returns:
        Volume-adjusted audio data
    """
    return audio_data * volume_factor


# [Utility]- Gain ctrl - Method 2
#  Decibel-based volume control (more intuitive for human hearing)
def adjust_volume_db(audio_data, db_adjustment):
    """
    Adjust volume using decibels (logarithmic scale).

    Args:
        audio_data: Audio samples as numpy array
        db_adjustment: Decibel adjustment:
                      0 dB = original volume
                     -6 dB = half perceived loudness
                    -12 dB = quarter perceived loudness
                     +6 dB = double perceived loudness (be careful with clipping)

    Returns:
        Volume-adjusted audio data
    """
    # Convert dB to amplitude factor
    amplitude_factor = 10 ** (db_adjustment / 20)
    return audio_data * amplitude_factor


# [Utility]
def find_device_by_name(device_name):
    """
    Find a device by its name and return its index.

    Args:
        device_name: Full or partial name of the device

    Returns:
        Index of the device or None if not found
    """
    devices = sd.query_devices()

    # Try exact match first
    for i, device in enumerate(devices):
        if device["name"] == device_name:
            return i

    # Try partial match
    for i, device in enumerate(devices):
        if device_name.lower() in device["name"].lower():
            return i

    return None


# [Utility]
def list_available_devices():
    """
    List all available audio devices with details.

    Returns:
        List of output devices with their indices
    """
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


# [Utility]
def confirm_selected_device(device=None, target_channels=2, channel_mapping=None):
    """Validate and configure a sound device for audio playback."""
    device_index = None
    device_info = None

    # Default channel mapping if needed
    if channel_mapping is None:
        channel_mapping = [1] * target_channels

    # Get device index
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
        target_channels = available_channels
        if len(channel_mapping) > target_channels:
            channel_mapping = channel_mapping[:target_channels]

    return device_info, device_index, target_channels, channel_mapping


# [state] - Output channel and other feature ctrl
def play_audio_stream(
    audio_file,
    device=None,  # Default output sound device
    volume_factor=1.0,
    target_sample_rate=48000,  # Should match output sound device's sample rate
    target_channels=2,
    channel_mapping=None,
):
    """
    Play audio using sounddevice.Stream with real-time transformation.
    This approach gives more control over the audio processing pipeline
    and allows for real-time adjustments.

    Args:
        audio_data: Original audio file
        device: Sound device to use (index or name) None is default
        volume_factor: 0.0-1.0
        orig_sample_rate: Original sample rate
        target_sample_rate: Target sample rate
        target_channels: Number of channels for output
        channel_mapping: Which channels to play audio on (0-indexed)

    Returns:
        tuple: (success, transformed_audio)
    """

    # Default channel mapping if not provided
    if channel_mapping is None:
        channel_mapping = [1] * target_channels

    # Step 1: Validate device and parameters using utility function
    device_info, device_index, target_channels, channel_mapping = (
        confirm_selected_device(
            device=device,
            target_channels=target_channels,
            channel_mapping=channel_mapping,
        )
    )

    # Step 2: Load the audio data
    audio_data_orig, orig_sample_rate = load_audio_file(audio_file)

    # Step 3: Apply volume adjustment
    audio_data = adjust_volume_linear(audio_data_orig, volume_factor)

    # Step 4: Resample the audio data
    new_length = int(len(audio_data) * target_sample_rate / orig_sample_rate)
    resampled_data = signal.resample(audio_data, new_length)

    # Step 5: Apply channel mask
    target_channels = len(channel_mapping)
    multichannel_audio = np.zeros((len(resampled_data), target_channels))
    # Apply the binary mask (multiply each channel by 0 or 1)
    for channel_idx, enabled in enumerate(channel_mapping):
        if enabled:
            multichannel_audio[:, channel_idx] = resampled_data

    # Step 6: Create callback for streaming
    position = 0

    def callback(outdata, frames, time, status):
        nonlocal position

        if status:
            print(status)

        # Check if we have enough data left
        remaining = len(multichannel_audio) - position
        if remaining < frames:
            # Not enough data left, pad with zeros
            outdata[:remaining] = multichannel_audio[position : position + remaining]
            outdata[remaining:] = 0
            raise sd.CallbackStop
        else:
            # Output the next chunk of audio
            outdata[:] = multichannel_audio[position : position + frames]
            position += frames

    # Step 5: Create and start the stream
    print(f"{Fore.GREEN}Starting playback:{Style.RESET_ALL}")
    print(f"  • Volume level: {volume_factor}")
    print(f"  • Sample rate: {target_sample_rate} Hz")
    # Show active channels in a human-readable way
    active_channels = [i + 1 for i, enabled in enumerate(channel_mapping) if enabled]
    print(f"  • Active channels: {active_channels} of {len(channel_mapping)} total")
    # Show device information
    if device_info is not None:
        print(f"  • Device: {device_info['name']} (index {device_index})")
    else:
        default_device = sd.query_devices(sd.default.device[1])
        print(f"  • Device: {default_device['name']} (default)")

    try:
        with sd.OutputStream(
            samplerate=target_sample_rate,
            channels=target_channels,
            callback=callback,
            device=device_index,  # Use the selected device
        ):
            print(
                f"Playing audio on {target_channels} channels at {target_sample_rate}Hz"
            )
            # print(f"Audio mapped to channels: {[ch + 1 for ch in channel_mapping]}")
            print(
                f"Audio mapped to channels: {active_channels} of {len(channel_mapping)} total"
            )

            # Calculate the wait time in milliseconds Wait until playback is finished
            duration_ms = int(1000 * len(multichannel_audio) / target_sample_rate)
            print(f"  • Duration: {duration_ms / 1000:.2f} seconds")
            sd.sleep(duration_ms)
        print(f"{Fore.GREEN}Playback complete!{Style.RESET_ALL}")
        return True, multichannel_audio
    except sd.PortAudioError as e:
        print(f"{Fore.RED}Error opening sound device: {e}{Style.RESET_ALL}")
        # If this is not the default device, try falling back to default
        if device_index is not None and device_index != sd.default.device[1]:
            print(f"{Fore.YELLOW}Falling back to default device...{Style.RESET_ALL}")
            return play_audio_stream(
                audio_file,
                device=None,
                volume_factor=volume_factor,
                target_sample_rate=target_sample_rate,
                target_channels=target_channels,
                channel_mapping=channel_mapping,
            )
        return False, None
    except Exception as e:
        print(f"Error in stream playback: {e}")
        return False, None


def main():
    """
    Main application function that ... and ... output channel settings
    """

    global wav_files, audio_file_exists

    # 1. List devices
    list_available_devices()

    # 2. Validate device and parameters
    device_info, device_index, target_channels, channel_mapping = (
        confirm_selected_device(
            device=TARGET_SOUND_DEVICE,
            target_channels=TARGET_TOTAL_CHANNELS,
            channel_mapping=TARGET_CHANNEL_MASK,
        )
    )

    print(
        f"\n{Fore.LIGHTMAGENTA_EX}Selected device:{Style.RESET_ALL}\n\t{Fore.LIGHTBLUE_EX}ID:{Style.RESET_ALL} {device_index}\n\t{Fore.LIGHTBLUE_EX}Name:{Style.RESET_ALL} {device_info['name']}\n"
    )

    # 3. Load audio file
    # Load the first .wav file found
    selected_wav_file = None
    if audio_file_exists:
        selected_wav_file = wav_files[
            0
        ]  # Use first file, or implement some other file selection

    # 4. Stream playback on desired channel at desired sample rate and at desired player volume
    success, transformed_audio = play_audio_stream(
        selected_wav_file,
        device=TARGET_SOUND_DEVICE,
        volume_factor=TARGET_VOLUME_FACTOR,
        target_sample_rate=TARGET_SAMPLE_RATE,
        target_channels=TARGET_TOTAL_CHANNELS,
        channel_mapping=TARGET_CHANNEL_MASK,
    )

    if not success or transformed_audio is None:
        print(
            "Playback error"
        )  # [Optional] More debug with breaks in these conditions and more prints of data
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(
            f"\n{Fore.YELLOW}Process interrupted by user. Exiting...{Style.RESET_ALL}"
        )
        sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}Unexpected error:{Style.RESET_ALL} {e}")
        sys.exit(1)

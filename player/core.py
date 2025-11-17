"""
Audio Player class with MQTT integration and real-time controls.
"""

import os
import json
import queue
import threading
from enum import Enum

import time

import numpy as np
from scipy import signal
import soundfile as sf
import sounddevice as sd
from colorama import Fore, Style


class PlayerState(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


def find_device_by_name(device_name):
    """Find a device by its name and return its index, preferring output devices."""
    devices = sd.query_devices()
    
    # First pass: exact match among OUTPUT devices only
    for device in devices:
        if (device["name"] == device_name and 
            device["max_output_channels"] > 0):
            return device['index']  # ← Correct device index
    
    # Fallback
    for device in devices:
        if device["name"] == device_name:
            return device['index']
    
    return None

class AudioPlayer:
    def __init__(
        self,
        device=None,
        volume_factor=1.0,
        target_sample_rate=48000,
        target_channels=2,
        channel_mapping=None,
        volume_step=0.25,
        audio_level_enabled=False,
    ):
        # Device configuration
        self.device = device
        # ------- CRITICAL FIX ------- #
        # Ensure device_index is always set correctly for Windows
        if isinstance(device, str):
            self.device_index = find_device_by_name(device)
            if self.device_index is None:
                print(f"Warning: Device '{device}' not found, using default")
                self.device_index = None  # Let sounddevice use system default
        elif isinstance(device, int):
            self.device_index = device
        else:
            self.device_index = None  # Use system default
        # -------- DEBUG INFO ------- #
        #  For Troubleshooting device info between OSs
        if self.device_index is not None:
            try:
                device_info = sd.query_devices(self.device_index)
                print(f"{Fore.CYAN}[DEVICE] Resolved device: {device_info['name']} (index: {self.device_index}){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}[DEVICE] Error querying device {self.device_index}: {e}{Style.RESET_ALL}")
                self.device_index = None
        else:
            print(f"{Fore.YELLOW}[DEVICE] Using system default audio device{Style.RESET_ALL}")
        # --------------------------- #
        self.target_sample_rate = target_sample_rate
        self.target_channels = target_channels
        self.channel_mapping = channel_mapping or [1] * target_channels
        self.dynamic_channel_mask = None  # ** Dynamic channel mask support: Will override channel_mapping when set

        # Volume control
        self.initial_volume_factor = volume_factor
        self.current_volume_factor = volume_factor
        self.volume_step = volume_step
        self.original_audio_data = None

        # Player state
        self.state = PlayerState.STOPPED
        self.loop_enabled = False
        self.position = 0
        self.audio_data = None
        self.multichannel_audio = None
        self.multichannel_template = None
        self.resampled_original = None
        self.stream = None
        self.audio_length = 0

        # Repeat mode state
        self.repeat_enabled = False
        self.repeat_count = 0
        self.repeat_interval = 0.0
        self.repeat_current = 0
        self.repeat_thread = None
        self.repeat_cancel_event = threading.Event()
        self.repeat_params_lock = threading.Lock()

        # Audio level tracking
        self.audio_level_enabled = audio_level_enabled
        if self.audio_level_enabled:
            self.current_audio_level = 0.0
            self.level_smoothing_factor = 0.3  # 0.1 = smooth, 0.9 = reactive
            self.level_normalization_factor = 1.0  # Will adapt dynamically
            self.normalized_audio_level = 0.0

        # Threading and control
        self.control_queue = queue.Queue()
        self.stop_event = threading.Event()
        
        # NEW - Playback health monitoring
        self.playback_health = {
            'last_position_update': time.time(),
            'stalled_count': 0,
            'position_check_interval': 5.0,  # Increased from 2.0 to 5.0 seconds
            'callback_calls': 0,
            'callback_errors': 0,
            'last_error_time': None
        }
        # ---

        # Atomic template swapping infrastructure
        self._pending_template = None  # New template waiting to be swapped
        self._pending_template_mapping = None  # Channel mapping for pending template
        self._template_swap_lock = (
            threading.Lock()
        )  # Thread safety for template operations
        self._template_creation_thread = None  # Background thread for template creation

        # MQTT integration
        self.mqtt_client = None
        self.auto_start_enabled = False
        self._last_published_state = None
        self._last_published_volume = None

    def set_mqtt_client(self, client):
        """
        Set MQTT client for state publishing.
        
        Args:
            client: MQTT client instance for publishing state updates
        """
        self.mqtt_client = client

    def set_auto_start(self, enabled):
        """
        Configure auto-start behavior.
        
        Args:
            enabled (bool): True to enable auto-start, False to disable
        """
        self.auto_start_enabled = enabled
        print(f"[PLAYER] Auto-start: {'ENABLED' if enabled else 'DISABLED'}")
    
    def _is_valid_wav_file(self, file_path):
        """
        Pre-flight check to see if a file is a valid WAV file that soundfile can handle.
        
        Validates channel count, sample rate, duration, and file integrity.
        
        Args:
            file_path (str): Path to WAV file to validate
        
        Returns:
            bool: True if file is valid, False otherwise
        """
        try:
            with sf.SoundFile(file_path, 'r') as f:
                # 1. Validate channel count
                if f.channels > 2:
                    print(f"\r{Fore.RED}[VALIDATION] Rejected: File has {f.channels} channels (max supported: 2){Style.RESET_ALL}")
                    return False

                # 2. Validate sample rate
                min_rate, max_rate = 8000, 96000
                if not (min_rate <= f.samplerate <= max_rate):
                    print(f"\r{Fore.RED}[VALIDATION] Rejected: Sample rate {f.samplerate}Hz is outside the allowed range ({min_rate}-{max_rate}Hz){Style.RESET_ALL}")
                    return False

                # 3. Validate duration (e.g., must be between 1 second and 2 hours)
                duration_seconds = f.frames / f.samplerate
                min_duration, max_duration_hours = 1, 2
                if not (min_duration <= duration_seconds <= max_duration_hours * 3600):
                    print(f"\r{Fore.RED}[VALIDATION] Rejected: Duration {duration_seconds:.2f}s is outside the allowed range ({min_duration}s - {max_duration_hours}hr){Style.RESET_ALL}")
                    return False
                
                # 4. Check if file is empty
                _ = f.frames
            return True
        except Exception as e:
            print(f"\r{Fore.RED}[VALIDATION] Invalid or corrupted WAV file: {os.path.basename(file_path)} - {e}{Style.RESET_ALL}")
            return False

    def _validate_channel_mask(self, mask):
        """
        Smart channel mask validation with truncation and padding.
        
        Returns:
            tuple: (is_valid: bool, processed_mask: list or None)
        """

        if not isinstance(mask, list):
            print(
                f"\r[CHANNEL_MASK] Invalid mask type: expected list, got {type(mask)}"
            )
            return False, None

        original_length = len(mask)
        processed_mask = mask.copy()

        # Handle different lengths
        if len(processed_mask) > self.target_channels:
            # Truncate if too long
            processed_mask = processed_mask[: self.target_channels]
            print(
                f"\r[CHANNEL_MASK] Truncated mask: {original_length} → {len(processed_mask)} channels"
            )

        elif len(processed_mask) < self.target_channels:
            # Pad if too short (but only if we have at least 2 channels)
            if len(processed_mask) >= 2:
                zeros_to_add = self.target_channels - len(processed_mask)
                processed_mask = processed_mask + [0] * zeros_to_add
                print(
                    f"\r[CHANNEL_MASK] Padded mask: {original_length} → {len(processed_mask)} channels (added {zeros_to_add} zeros)"
                )
            else:
                # Single channel doesn't make sense
                print(
                    f"\r[CHANNEL_MASK] Invalid mask length: {original_length} channel(s) insufficient (need ≥2)"
                )
                return False, None

        # Now validate all values are 0 or 1
        for i, value in enumerate(processed_mask):
            if not isinstance(value, int) or value not in [0, 1]:
                print(
                    f"\r[CHANNEL_MASK] Invalid mask value at index {i}: expected 0 or 1, got {value}"
                )
                return False, None

        print(f"\r[CHANNEL_MASK] Valid mask: {processed_mask}")
        if original_length != len(processed_mask):
            print(f"\r[CHANNEL_MASK] Original: {mask} → Processed: {processed_mask}")

        return True, processed_mask

    def set_dynamic_channel_mask(self, mask):
        """
        Set dynamic channel mask for future playback sessions.
        
        Returns:
            bool: True if mask was valid and applied, False otherwise
        """

        # Use smart validation that returns processed mask
        is_valid, processed_mask = self._validate_channel_mask(mask)

        if is_valid:
            old_mask = self.dynamic_channel_mask
            self.dynamic_channel_mask = processed_mask.copy()  # Use processed mask

            print(
                f"\r[CHANNEL_MASK] Dynamic mask updated: {old_mask} -> {processed_mask}"
            )

            # Check if we should apply instantly or wait
            if self.state == PlayerState.PLAYING:
                # Audio is playing - trigger instant switching!
                print("\r[CHANNEL_MASK] ⚡ Audio playing - triggering INSTANT switch")
                self._create_template_async(processed_mask)
            else:
                # Audio not playing - use traditional behavior
                print(
                    "\r[CHANNEL_MASK] Audio not playing - will apply on next start/restart"
                )

            return True
        else:
            print(f"\r[CHANNEL_MASK] Ignoring invalid channel mask: {mask}")
            return False

    def get_active_channel_mapping(self):
        """
        Get the currently active channel mapping.
        
        Returns:
            list: Active channel mapping (dynamic mask if set, otherwise default)
        """
        return (
            self.dynamic_channel_mask
            if self.dynamic_channel_mask is not None
            else self.channel_mapping
        )

    def _create_multichannel_template(self, channel_mapping):
        """
        Create multichannel audio template for given channel mapping.
        
        Returns:
            numpy.ndarray or None: Multichannel template (samples x channels), or None on failure
        """
        if self.resampled_original is None:
            print("\r[TEMPLATE] No resampled audio data available")
            return None

        print(f"\r[TEMPLATE] Creating template with mapping: {channel_mapping}")

        # Create multichannel template (samples x channels)
        template = np.zeros((len(self.resampled_original), len(channel_mapping)))

        # Fill enabled channels with audio data
        for channel_idx, enabled in enumerate(channel_mapping):
            if enabled:
                template[:, channel_idx] = self.resampled_original

        print(f"\r[TEMPLATE] Created template: {template.shape} (samples x channels)")
        return template

    def _create_template_async(self, channel_mapping):
        """
        Create multichannel template in background thread for atomic swapping.
        
        Enables glitch-free channel mask changes during playback by preparing
        new template in background and swapping atomically in audio callback.
        
        Args:
            channel_mapping (list): New channel mask to apply
        """

        def background_template_creation():
            try:
                print(f"\r[INSTANT] Creating template in background: {channel_mapping}")

                # Create new template (this can take time, but it's in background)
                new_template = self._create_multichannel_template(channel_mapping)

                if new_template is not None:
                    # Atomically set the pending template (thread-safe)
                    with self._template_swap_lock:
                        self._pending_template = new_template
                        self._pending_template_mapping = channel_mapping.copy()

                    print(
                        f"\r[INSTANT] Background template ready for swap: {channel_mapping}"
                    )
                else:
                    print("\r[INSTANT] Background template creation failed")

            except Exception as e:
                print(f"\r[INSTANT] Background template error: {e}")

        # Start background thread (don't block MQTT handler)
        if (
            self._template_creation_thread is None
            or not self._template_creation_thread.is_alive()
        ):
            self._template_creation_thread = threading.Thread(
                target=background_template_creation
            )
            self._template_creation_thread.daemon = True
            self._template_creation_thread.start()
        else:
            print("\r[INSTANT] Template creation already in progress, ignoring request")

    def _check_and_swap_pending_template(self):
        """
        Check if there's a pending template and swap it atomically.
        Called from audio callback - must be FAST!
        
        Returns:
            bool: True if template was swapped, False if no pending template
        """
        # Quick check without lock first (performance optimization)
        if self._pending_template is None:
            return False

        # Atomic swap (very fast operation)
        try:
            with self._template_swap_lock:
                if self._pending_template is not None:
                    # Swap templates atomically
                    old_mapping = getattr(self, "_template_channel_mapping", None)

                    self.multichannel_template = self._pending_template
                    self._template_channel_mapping = (
                        self._pending_template_mapping.copy()
                    )
                    self.audio_length = len(self.multichannel_template)

                    # Clear pending template
                    self._pending_template = None
                    self._pending_template_mapping = None

                    print(
                        f"\r[INSTANT] ⚡ Template swapped! {old_mapping} → {self._template_channel_mapping}"
                    )
                    return True
        except Exception as e:
            print(f"\r[INSTANT] Template swap error: {e}")

        return False

    def load_audio_file(self, audio_file):
        """
        Load and prepare audio file for playback.
        
        Returns:
            bool: True if file loaded successfully, False otherwise
        """
        print(
            f"\r{Fore.LIGHTCYAN_EX}Loading audio file:{Style.RESET_ALL} {os.path.basename(audio_file)}"
        )

        try:
            # Load audio data and get original sample rate
            audio_data_array, orig_sample_rate = sf.read(audio_file)

            print(f"\r  • Original sample rate: {orig_sample_rate} Hz")
            print(
                f"\r  • Audio duration: {len(audio_data_array) / orig_sample_rate:.2f} seconds"
            )
            print(f"\r  • Audio shape: {audio_data_array.shape}")

            # Convert to mono if stereo
            if len(audio_data_array.shape) > 1:
                audio_data_array = np.mean(audio_data_array, axis=1)
                print("\r  • Converted to mono")

            # Store original audio data (no volume applied yet)
            self.original_audio_data = audio_data_array

            # Resample the original audio data
            new_length = int(
                len(self.original_audio_data)
                * self.target_sample_rate
                / orig_sample_rate
            )

            self.resampled_original = signal.resample(
                self.original_audio_data, new_length
            )

            # Use active channel mapping instead of self.channel_mapping
            active_channel_mapping = self.get_active_channel_mapping()

            print(f"\r  Using channel mapping: {active_channel_mapping}")

            self.multichannel_template = self._create_multichannel_template(
                active_channel_mapping
            )

            if self.multichannel_template is None:
                print(f"\r{Fore.RED}Failed to create audio template{Style.RESET_ALL}")
                return False

            self.audio_length = len(self.multichannel_template)
            self.position = 0

            # Remember which mapping was used for this template
            self._template_channel_mapping = active_channel_mapping.copy()

            print(f"\r{Fore.GREEN}Audio loaded successfully!{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"\r{Fore.RED}Error loading audio file: {e}{Style.RESET_ALL}")
            return False

    def get_time_string(self, position_samples):
        """
        Convert sample position to time string (MM:SS).
        
        Args:
            position_samples (int): Sample position to convert
        
        Returns:
            str: Time string in MM:SS format
        """
        seconds = position_samples / self.target_sample_rate
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_total_time_string(self):
        """
        Get total audio duration as time string.
        
        Returns:
            str: Total duration in MM:SS format
        """
        return self.get_time_string(self.audio_length)

    def get_volume_percentage(self):
        """
        Get current volume as percentage.
        
        Returns:
            int: Current volume as percentage (0-200)
        """
        return int(self.current_volume_factor * 100)

    def get_status_line(self):
        """
        Get current status line for display.
        
        Returns:
            str: Formatted status line with state, time, loop, volume, and controls
        """
        current_time = self.get_time_string(self.position)
        total_time = self.get_total_time_string()
        state_str = self.state.value.upper()
        loop_str = "LOOP" if self.loop_enabled else "    "
        volume_str = f"Vol:{self.get_volume_percentage()}%"

        return f"[{state_str:7}] {current_time}/{total_time} [{loop_str}] [{volume_str:8}] | S:Start/Stop P:Play/Pause L:Loop +/-:Volume Q:Quit"

    def calculate_rms_level(self, audio_chunk):
        """
        Calculate RMS (Root Mean Square) level from audio chunk.
        
        Args:
            audio_chunk (numpy.ndarray): Audio chunk to analyze
        
        Returns:
            float: Normalized RMS level (0.0-1.0)
        """
        if not self.audio_level_enabled or audio_chunk is None or len(audio_chunk) == 0:
            return 0.0
        # Calculate RMS across all channels
        rms = np.sqrt(np.mean(audio_chunk**2))
        # Apply smoothing
        self.current_audio_level = (
            self.current_audio_level * (1 - self.level_smoothing_factor)
            + rms * self.level_smoothing_factor
        )
        # Normalize to 0-1 range (adaptive)
        normalized_level = min(
            1.0, self.current_audio_level * self.level_normalization_factor
        )
        return normalized_level

    def _get_repeat_state(self):
        """
        Get current repeat state for status reporting.
        
        Returns:
            str or None: 'playing', 'waiting', 'completed', or None if repeat disabled
        """
        if not self.repeat_enabled:
            return None
        
        # Check if we're currently playing or waiting between plays
        if self.state == PlayerState.PLAYING:
            return "playing"
        elif self.state == PlayerState.STOPPED and self.repeat_current < self.repeat_count:
            return "waiting"
        else:
            return "completed"

    def publish_player_state(self):
        """
        Publish current player state to MQTT.
        
        Publishes state, volume, loop status, and repeat information if active.
        """
        if not self.mqtt_client:
            return

        try:
            # This will be set by the MQTT module
            if hasattr(self, "_mqtt_config"):
                status_topic = self._mqtt_config["pub"]["topics"]["player_status"]
                state_data = {
                    "state": self.state.value,
                    "loop_enabled": self.loop_enabled,
                    "volume": round(self.current_volume_factor, 2),
                    "volume_percentage": self.get_volume_percentage(),
                    "auto_start": self.auto_start_enabled,
                }

                # Add repeat information if repeat mode is active
                if self.repeat_enabled:
                    state_data.update({
                        "repeat_enabled": True,
                        "repeat_current": self.repeat_current,
                        "repeat_total": self.repeat_count,
                        "repeat_interval": self.repeat_interval,
                        "repeat_state": self._get_repeat_state()
                    })

                self.mqtt_client.publish(status_topic, json.dumps(state_data))
                
                # Enhanced logging with repeat info
                log_msg = f"\r[MQTT] >>> State: {self.state.value}, Vol: {self.get_volume_percentage()}%, Loop: {self.loop_enabled}"
                if self.repeat_enabled:
                    log_msg += f", Repeat: {self.repeat_current}/{self.repeat_count}"
                print(log_msg)

        except Exception as e:
            print(f"\r[MQTT] State publish error: {e}")

    def check_and_publish_state_changes(self):
        """
        Check if state or volume changed and publish if needed.
        
        Compares current state with last published state and triggers publish on changes.
        """
        current_state = (
            self.state.value,
            self.current_volume_factor,
            self.loop_enabled,
            self.repeat_enabled,
            self.repeat_current if self.repeat_enabled else 0,
        )

        if self._last_published_state != current_state:
            self.publish_player_state()
            self._last_published_state = current_state

    def audio_callback(self, outdata, frames, time_info, status):
        """
        Audio stream callback function.
        
        Called by sounddevice for each audio buffer. Handles playback and monitoring.
        """
        # Increment callback counter
        self.playback_health['callback_calls'] += 1
        
        # Log any audio system warnings/errors
        if status:
            self.playback_health['callback_errors'] += 1
            self.playback_health['last_error_time'] = time.time()

        # Process control commands
        self._process_control_commands()

        if self.state != PlayerState.PLAYING:
            outdata.fill(0)
            return

        # Handle audio playback
        self._handle_audio_playback(outdata, frames)

    def _process_control_commands(self):
        """
        Process queued control commands.
        
        Handles play, pause, stop, start, volume changes from control queue.
        """
        try:
            while not self.control_queue.empty():
                command = self.control_queue.get_nowait()
                old_state = self.state
                old_volume = self.current_volume_factor

                if command == "pause":
                    self.state = PlayerState.PAUSED
                elif command == "play":
                    self.state = PlayerState.PLAYING
                elif command == "stop":
                    self.state = PlayerState.STOPPED
                    self.position = 0
                elif command == "start":
                    # Check for channel mask changes before starting
                    self._check_and_update_channel_template()
                    self.state = PlayerState.PLAYING
                    self.position = 0
                elif command == "volume_up":
                    self.current_volume_factor = min(
                        2.0, self.current_volume_factor + self.volume_step
                    )
                elif command == "volume_down":
                    self.current_volume_factor = max(
                        0.0, self.current_volume_factor - self.volume_step
                    )

                # Check for state changes
                if old_state != self.state or old_volume != self.current_volume_factor:
                    self.check_and_publish_state_changes()

        except queue.Empty:
            pass

    def _handle_audio_playback(self, outdata, frames):
        """
        Handle audio playback logic.
        
        Manages audio buffer filling, looping, and position tracking.
        """

        # NEW: Check for instant template swapping (VERY FAST)
        self._check_and_swap_pending_template()

        remaining = self.audio_length - self.position

        if remaining <= 0:
            if self.loop_enabled:
                self._check_and_update_channel_template()
                self.position = 0
                remaining = self.audio_length
            else:
                outdata.fill(0)
                old_state = self.state
                self.state = PlayerState.STOPPED
                self.position = 0
                if old_state != self.state:
                    self.check_and_publish_state_changes()
                return

        if remaining < frames:
            if self.loop_enabled:
                # Fill partial frame and loop
                chunk1 = (
                    self.multichannel_template[
                        self.position : self.position + remaining
                    ]
                    * self.current_volume_factor
                )
                outdata[:remaining] = chunk1
                self._check_and_update_channel_template()
                self.position = 0
                remaining_frames = frames - remaining
                chunk2 = (
                    self.multichannel_template[:remaining_frames]
                    * self.current_volume_factor
                )
                outdata[remaining:] = chunk2
                self.position = remaining_frames
            else:
                # Fill what we can, pad with zeros
                chunk = (
                    self.multichannel_template[
                        self.position : self.position + remaining
                    ]
                    * self.current_volume_factor
                )
                outdata[:remaining] = chunk
                outdata[remaining:] = 0
                old_state = self.state
                self.state = PlayerState.STOPPED
                self.position = 0
                if old_state != self.state:
                    self.check_and_publish_state_changes()
        else:
            # Normal playback
            chunk = (
                self.multichannel_template[self.position : self.position + frames]
                * self.current_volume_factor
            )
            outdata[:] = chunk
            self.position += frames
            if self.audio_level_enabled:
                self.normalized_audio_level = self.calculate_rms_level(chunk)

    def start_stream(self):
        """
        Start the audio stream.
        
        Returns:
            bool: True if stream started successfully, False otherwise
        """
        active_channel_mapping = self.get_active_channel_mapping()

        try:
            self.stream = sd.OutputStream(
                samplerate=self.target_sample_rate,
                channels=len(active_channel_mapping),
                callback=self.audio_callback,
                device=self.device_index,
                blocksize=1024,
            )
            self.stream.start()
            return True
        except Exception as e:
            print(f"{Fore.RED}Error starting audio stream: {e}{Style.RESET_ALL}")
            return False

    def stop_stream(self):
        """
        Stop the audio stream.
        
        Closes and cleans up the sounddevice output stream.
        """
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _check_and_update_channel_template(self):
        """
        Check if channel mask changed and update multichannel template if needed.
        
        Recreates audio template if channel mapping has changed.
        """
        if self.resampled_original is None:
            return

        current_active_mapping = self.get_active_channel_mapping()

        # Store the mapping that was used to create current template
        if not hasattr(self, "_template_channel_mapping"):
            self._template_channel_mapping = None

        # Check if template needs updating:
        # 1. Template doesn't exist
        # 2. Channel count changed
        # 3. Channel mapping changed (THIS WAS MISSING!)
        needs_update = (
            self.multichannel_template is None
            or self.multichannel_template.shape[1] != len(current_active_mapping)
            or self._template_channel_mapping != current_active_mapping
        )

        if needs_update:
            print(
                f"\r[CHANNEL_MASK] Updating template for loop with mapping: {current_active_mapping}"
            )
            print(
                f"\r[CHANNEL_MASK] Previous mapping was: {self._template_channel_mapping}"
            )

            # Recreate multichannel template with new mapping
            self.multichannel_template = self._create_multichannel_template(
                current_active_mapping
            )

            self.audio_length = len(self.multichannel_template)

            # Remember which mapping was used for this template
            self._template_channel_mapping = current_active_mapping.copy()

            print(
                f"\r[CHANNEL_MASK] Template updated - now using {len(current_active_mapping)} channels: {current_active_mapping}"
            )

            # Need to restart audio stream with new channel count
            self._restart_stream_if_needed(current_active_mapping)

    def _restart_stream_if_needed(self, new_channel_mapping):
        """
        Restart audio stream if channel count changed.
        
        Args:
            new_channel_mapping (list): New channel mapping to apply
        """
        if self.stream is None:
            return

        current_channels = self.stream.channels
        new_channels = len(new_channel_mapping)

        if current_channels != new_channels:
            print(
                f"\r[CHANNEL_MASK] Restarting stream: {current_channels} → {new_channels} channels"
            )

            # Stop current stream
            self.stream.stop()
            self.stream.close()

            # Start new stream with correct channel count
            self.stream = sd.OutputStream(
                samplerate=self.target_sample_rate,
                channels=new_channels,
                callback=self.audio_callback,
                device=self.device_index,
                blocksize=1024,
            )
            self.stream.start()

    def send_command(self, command):
        """
        Send a command to the audio thread.
        
        Args:
            command (str): Command to send (e.g., 'play', 'pause', 'stop')
        """
        self.control_queue.put(command)

    # Control methods
    def start_playback(self):
        """
        Start playback from beginning.
        
        Triggers repeat mode if enabled, otherwise starts normal single playback.
        """
        # Check if repeat mode is enabled
        if self.repeat_enabled:
            # Spawn repeat worker if not already running
            if self.repeat_thread is None or not self.repeat_thread.is_alive():
                print(f"\r[REPEAT] Triggering repeat mode: {self.repeat_count}x with {self.repeat_interval}s interval")
                self.repeat_current = 0
                self.repeat_cancel_event.clear()
                self.repeat_thread = threading.Thread(
                    target=self._repeat_playback_worker,
                    daemon=True
                )
                self.repeat_thread.start()
            else:
                print(f"\r[REPEAT] Repeat worker already active")
        else:
            # Normal single playback
            self.send_command("start")

    def stop_playback(self):
        """
        Stop playback and reset to beginning.
        
        Resets position to start of audio.
        """
        self.send_command("stop")

    def play_pause_toggle(self):
        """
        Toggle between play and pause.
        
        Pauses if playing, resumes if paused.
        """
        if self.state == PlayerState.PLAYING:
            self.send_command("pause")
            print(f"\r⏸ PAUSED at {self.get_time_string(self.position)}")
        else:
            self.send_command("play")
            print(f"\r▶ PLAYING from {self.get_time_string(self.position)}")

    def start_stop_toggle(self):
        """
        Toggle between start and stop.
        
        Starts from beginning if stopped, stops if playing/paused.
        """
        if self.state == PlayerState.STOPPED:
            self.send_command("start")
            print(
                f"\r▶ STARTED - {self.get_time_string(self.position)}/{self.get_total_time_string()}"
            )
        else:
            self.send_command("stop")
            print("\r⏹ STOPPED")

    def toggle_loop(self):
        """
        Toggle loop mode.
        
        Enables looping if disabled, disables if enabled.
        """
        self.loop_enabled = not self.loop_enabled
        loop_status = "ENABLED" if self.loop_enabled else "DISABLED"
        print(f"\r Loop: {loop_status}")
        self.check_and_publish_state_changes()

    def volume_up(self):
        """
        Increase volume.
        
        Increases volume by configured step amount.
        """
        self.send_command("volume_up")

    def volume_down(self):
        """
        Decrease volume.
        
        Decreases volume by configured step amount.
        """
        self.send_command("volume_down")

    def seek_to_position(self, target_samples):
        """
        Seek to a specific position in samples.
        
        Returns:
            bool: True if seek was successful, False if position out of range
        """
        if 0 <= target_samples <= self.audio_length:
            self.position = target_samples
            return True
        return False

    def seek_to_time(self, target_seconds):
        """
        Seek to a specific time in seconds.
        
        Returns:
            bool: True if seek was successful, False if time out of range
        """
        target_samples = int(target_seconds * self.target_sample_rate)
        return self.seek_to_position(target_samples)
    
    # Repeat playback control methods
    def start_repeat_playback(self, count, interval):
        """
        Set repeat parameters (PASSIVE - does not start playback).
        Playback will follow repeat behavior when triggered via start_playback().
        Args:
            count: Number of times to play audio (1-10)
            interval: Seconds to wait between plays (0-30)
        """
        with self.repeat_params_lock:
            # Cancel any existing repeat worker
            if self.repeat_enabled and self.repeat_thread and self.repeat_thread.is_alive():
                self._cancel_repeat_internal()
                print(f"\r[REPEAT] Previous repeat worker cancelled")
            
            # Disable loop mode when repeat is activated
            if self.loop_enabled:
                self.loop_enabled = False
                print(f"\r[REPEAT] Loop disabled - repeat mode will take priority")
            
            # Set new repeat parameters
            self.repeat_enabled = True
            self.repeat_count = count
            self.repeat_interval = interval
            self.repeat_current = 0
            self.repeat_cancel_event.clear()
            
            print(f"\r[REPEAT] Behavior set: {count}x with {interval}s interval (waiting for playback trigger)")
    
    def cancel_repeat(self):
        """
        Cancel repeat playback mode (public interface).
        
        Stops repeat mode and returns to single-play behavior.
        """
        with self.repeat_params_lock:
            if self.repeat_enabled:
                self._cancel_repeat_internal()
                print(f"\r[REPEAT] Repeat cancelled - returning to single-play mode")
                self.check_and_publish_state_changes()
            else:
                print(f"\r[REPEAT] No active repeat to cancel")
    
    def _cancel_repeat_internal(self):
        """
        Internal method to cancel repeat (assumes lock is already held).
        
        Disables repeat mode and signals worker thread to exit.
        """
        self.repeat_enabled = False
        self.repeat_cancel_event.set()
        
        # Wait for thread to finish (with timeout)
        if self.repeat_thread and self.repeat_thread.is_alive():
            self.repeat_thread.join(timeout=0.5)
    
    def _interruptible_sleep(self, duration):
        """
        Sleep for specified duration, but can be interrupted by cancel_event OR pause. Part fo repeat behavior
        Args:
            duration: Sleep duration in seconds
        Returns:
            bool: True if completed normally, False if interrupted by cancellation
        """
        # Sleep in small intervals to allow quick cancellation
        sleep_quantum = 0.1  # Check every 100ms
        elapsed = 0.0
        
        while elapsed < duration:
            if self.repeat_cancel_event.is_set():
                return False  # Interrupted by cancel
            
            # Check if paused during interval
            if self.state == PlayerState.PAUSED:
                # Wait for resume or cancellation
                while self.state == PlayerState.PAUSED:
                    if self.repeat_cancel_event.is_set():
                        return False
                    time.sleep(0.1)
                # Resumed - continue interval
            
            time.sleep(min(sleep_quantum, duration - elapsed))
            elapsed += sleep_quantum
        
        return True  # Completed normally
    
    def _repeat_playback_worker(self):
        """
        Background thread that manages repeat playback cycles.
        Runs until repeat_count is reached or cancelled.
        """
        print(f"\r[REPEAT] Worker thread started")
        
        try:
            for i in range(self.repeat_count):
                # Check for cancellation
                if self.repeat_cancel_event.is_set():
                    print(f"\r[REPEAT] Worker cancelled at iteration {i+1}")
                    with self.repeat_params_lock:
                        self.repeat_current = 0  # Reset counter
                    return
                
                # Update current repetition number
                with self.repeat_params_lock:
                    self.repeat_current = i + 1
                
                print(f"\r[REPEAT] Starting play {self.repeat_current}/{self.repeat_count}")
                
                # CRITICAL FIX: Call send_command directly, not start_playback()
                # (start_playback checks repeat_enabled and would try to spawn another worker)
                self.send_command("start")
                
                # Give playback a moment to actually start
                time.sleep(0.1)
                
                # NOW publish state (after playback started)
                self.check_and_publish_state_changes()
                
                # Wait for playback to finish (or pause)
                while self.state == PlayerState.PLAYING:
                    if self.repeat_cancel_event.is_set():
                        print(f"\r[REPEAT] Cancelled during playback")
                        with self.repeat_params_lock:
                            self.repeat_current = 0  # Reset counter
                        return
                    
                    # Check if loop was enabled during play (loop takes priority)
                    if self.loop_enabled:
                        with self.repeat_params_lock:
                            self.repeat_enabled = False
                        print(f"\r[REPEAT] Loop enabled - handing over to loop mode")
                        return
                    
                    time.sleep(0.1)
                
                # Check if paused (wait for resume or cancellation)
                while self.state == PlayerState.PAUSED:
                    if self.repeat_cancel_event.is_set():
                        print(f"\r[REPEAT] Cancelled while paused")
                        with self.repeat_params_lock:
                            self.repeat_current = 0  # Reset counter
                        return
                    
                    # Check if loop was enabled while paused
                    if self.loop_enabled:
                        with self.repeat_params_lock:
                            self.repeat_enabled = False
                        print(f"\r[REPEAT] Loop enabled while paused - handing over to loop mode")
                        return
                    
                    time.sleep(0.1)
                
                print(f"\r[REPEAT] Play {self.repeat_current}/{self.repeat_count} finished")
                
                # If not the last iteration, wait interval before next play
                if i < self.repeat_count - 1:
                    if self.repeat_interval > 0:
                        print(f"\r[REPEAT] Waiting {self.repeat_interval}s before next play (position: 00:00)")
                        
                        # Reset position to 00:00 during wait
                        self.position = 0
                        
                        # Interruptible sleep
                        if not self._interruptible_sleep(self.repeat_interval):
                            print(f"\r[REPEAT] Wait interrupted")
                            with self.repeat_params_lock:
                                self.repeat_current = 0  # Reset counter
                            return
            
            # All repetitions completed - KEEP repeat_enabled=True (STICKY BEHAVIOR)
            # Just reset counter, ready for next trigger
            with self.repeat_params_lock:
                self.repeat_current = 0  # Reset for next trigger
            
            print(f"\r[REPEAT] All {self.repeat_count} repetitions completed (repeat mode still active)")
            self.check_and_publish_state_changes()
            
        except Exception as e:
            print(f"\r[REPEAT] Worker error: {e}")
            with self.repeat_params_lock:
                self.repeat_current = 0  # Reset counter on error
        
        print(f"\r[REPEAT] Worker thread exiting")
    
    # NEW: Playback health monitoring
    def check_playback_health(self):
        """
        Detect if audio callback is stalled/frozen.
        
        Returns:
            dict: Health status with keys 'is_healthy', 'issues', and 'metrics'
        """
        # CRITICAL: Define health dict at the very start
        health = {
            'is_healthy': True,
            'issues': [],
            'metrics': {}
        }
        
        # Not playing is not an error
        if self.state != PlayerState.PLAYING:
            health['metrics']['state'] = self.state.value
            # During repeat intervals, audio is legitimately stopped
            if self.repeat_enabled and self.state == PlayerState.STOPPED:
                health['metrics']['repeat_waiting'] = True
            return health  # <-- Return the dict
        
        current_time = time.time()
        time_since_update = current_time - self.playback_health['last_position_update']
        
        try:
            # Check if position is advancing
            if self.position > 0:
                self.playback_health['last_position_update'] = current_time
            
            # Check for stall (position not advancing for too long)
            if time_since_update > self.playback_health['position_check_interval']:
                health['is_healthy'] = False
                health['issues'].append(f'position_stalled_{time_since_update:.1f}s')
            
            # Check callback error rate
            if self.playback_health['callback_calls'] > 0:
                error_rate = self.playback_health['callback_errors'] / self.playback_health['callback_calls']
                if error_rate > 0.01:  # More than 1% errors
                    health['is_healthy'] = False
                    health['issues'].append(f'high_error_rate_{error_rate:.2%}')
            
            # Add metrics
            health['metrics'] = {
                'callback_calls': self.playback_health['callback_calls'],
                'callback_errors': self.playback_health['callback_errors'],
                'time_since_update': round(time_since_update, 2),
                'position': self.position,
                'audio_length': self.audio_length
            }
            
        except Exception as e:
            health['is_healthy'] = False
            health['issues'].append(f'check_error: {str(e)}')
        
        return health  # <-- Always return the dict
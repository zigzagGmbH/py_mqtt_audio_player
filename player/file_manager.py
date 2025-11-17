"""
File manager for audio player - handles file downloads and management.
"""

import os
import time
import urllib.parse
import requests
from colorama import Fore, Style


class DownloadState:
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    DOWNLOAD_FAILED = "download_failed"
    REVERTED = "reverted"


class AudioFileManager:
    def __init__(self, audio_dir, auto_start_enabled=False):
        self.audio_dir = audio_dir
        self.auto_start_enabled = auto_start_enabled
        self.current_file = None
        self.previous_file = None
        self.was_playing = True

    def set_current_file(self, file_path):
        """Set the current audio file"""
        self.previous_file = self.current_file
        self.current_file = file_path
        
    def _load_absolute_file_path(self, file_path, mqtt_client, player, original_state):
        """Load audio file from absolute path on the same computer"""
        try:
            # Convert to Path object for cross-platform compatibility
            from pathlib import Path
            from player.utils import is_valid_audio_file
            
            audio_file_path = Path(file_path)
            
            # Validate file exists
            if not audio_file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
                
            # Validate it's an audio file
            if not audio_file_path.suffix.lower() == '.wav':
                raise ValueError(f"Unsupported audio format: {audio_file_path.suffix}")
            
            # Use existing validation for metadata/system files
            if not is_valid_audio_file(str(audio_file_path)):
                raise ValueError(f"Invalid audio file (likely system/metadata file): {audio_file_path.name}")
                
            print(f"\r[LOCAL_ABS] Loading absolute path: {file_path}")
            
            # Stop current playback
            player.send_command("stop")
            time.sleep(0.2)

            # Load new audio file
            if player.load_audio_file(str(audio_file_path)):
                # Update file tracking
                self.current_file = str(audio_file_path)

                # Apply auto-start logic (same as download)
                should_auto_start = False

                if self.auto_start_enabled:
                    should_auto_start = True
                    print(f"\r[AUTO-START] ▶ Auto-starting new file (auto-start enabled, was {original_state.value})")
                else:
                    print("\r[LOAD] ⏸ New file loaded, auto-start disabled - awaiting command")
                
                if should_auto_start:
                    player.start_playback()
                    time.sleep(0.1)

                # Publish success state
                if hasattr(mqtt_client, "publish_download_state"):
                    mqtt_client.publish_download_state(
                        DownloadState.DOWNLOADED,  # Reuse existing state
                        {
                            "loaded_file": audio_file_path.name,
                            "file_path": str(audio_file_path),
                            "is_absolute_path": True,
                            "auto_started": should_auto_start,
                        },
                    )

                print(f"\r[LOCAL_ABS] Successfully loaded: {audio_file_path.name}")
                return True
                
        except Exception as e:
            print(f"\r[LOCAL_ABS] Failed to load: {str(e)}")
            # Publish failure state
            if hasattr(mqtt_client, "publish_download_state"):
                mqtt_client.publish_download_state(
                    DownloadState.DOWNLOAD_FAILED,
                    {
                        "error_message": str(e),
                        "failed_path": file_path,
                        "is_absolute_path": True,
                    }
                )
            return False

    def download_audio_file(self, url, mqtt_client, player):
        """Download audio file from URL and update player"""
        try:
            # Store current file as previous
            self.previous_file = self.current_file

            # Remember original state
            original_state = player.state
            self.was_playing = player.state.value == "playing"
            
            # Save repeat parameters if repeat is active
            repeat_was_active = player.repeat_enabled
            saved_repeat_count = player.repeat_count if repeat_was_active else 0
            saved_repeat_interval = player.repeat_interval if repeat_was_active else 0.0
            
            if repeat_was_active:
                print(f"\r[DOWNLOAD] Saving repeat params: {saved_repeat_count}x with {saved_repeat_interval}s interval")
            
            # Check if this is a local file path instead of URL
            if not url.startswith(("http://", "https://")):
                # Treat as local file path
                result = self._load_absolute_file_path(url, mqtt_client, player, original_state)
                
                # Restart repeat if it was active
                if result and repeat_was_active:
                    print(f"\r[DOWNLOAD] Restarting repeat mode with saved params")
                    player.start_repeat_playback(saved_repeat_count, saved_repeat_interval)
                
                return result

            # Publish downloading state
            if hasattr(mqtt_client, "publish_download_state"):
                mqtt_client.publish_download_state(
                    DownloadState.DOWNLOADING,
                    {
                        "download_url": url,
                        "current_file": (
                            os.path.basename(self.current_file)
                            if self.current_file
                            else None
                        ),
                    },
                )

            print(
                f"\r[DOWNLOAD] {Fore.LIGHTYELLOW_EX}Starting download{Style.RESET_ALL} "
                f"from: {url} (keeping current playback)"
            )

            # Parse filename from URL
            parsed_url = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename or not filename.endswith(".wav"):
                filename = f"downloaded_audio_{int(time.time())}.wav"

            # Download path
            download_path = os.path.join(self.audio_dir, filename)

            # Download with progress
            print(
                f"\r[DOWNLOAD] {Fore.LIGHTYELLOW_EX}Downloading to{Style.RESET_ALL}: "
                f"{filename} (audio continues playing)"
            )
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # Save file
            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(
                f"\r[DOWNLOAD] {Fore.LIGHTGREEN_EX}Download completed{Style.RESET_ALL}: "
                f"{filename}"
            )

            # Handle player transition
            print(
                f"\r[DOWNLOAD] {Fore.LIGHTCYAN_EX}Switching to new audio file...{Style.RESET_ALL}"
            )

            # Stop current playback
            player.send_command("stop")
            time.sleep(0.2)

            # Load new audio file
            if player.load_audio_file(download_path):
                # Update file tracking
                self.current_file = download_path

                # Restore repeat parameters BEFORE starting playback
                if repeat_was_active:
                    print(f"\r[DOWNLOAD] Restoring repeat params: {saved_repeat_count}x with {saved_repeat_interval}s interval")
                    player.start_repeat_playback(saved_repeat_count, saved_repeat_interval)

                # Apply auto-start logic
                should_auto_start = False

                if self.auto_start_enabled:
                    should_auto_start = True
                    print(f"\r[AUTO-START] ▶ Auto-starting new file (auto-start enabled, was {original_state.value})")
                else:
                    print("\r[LOAD] ⏸ New file loaded, auto-start disabled - awaiting command")

                # Start playback if needed (will trigger repeat if enabled)
                if should_auto_start:
                    player.start_playback()
                    time.sleep(0.1)

                # Publish downloaded state
                if hasattr(mqtt_client, "publish_download_state"):
                    mqtt_client.publish_download_state(
                        DownloadState.DOWNLOADED,
                        {
                            "downloaded_file": filename,
                            "file_path": download_path,
                            "previous_file": (
                                os.path.basename(self.previous_file)
                                if self.previous_file
                                else None
                            ),
                            "original_state": original_state.value,
                            "auto_started": should_auto_start,
                            "repeat_restarted": repeat_was_active,
                            "transition_completed": True,
                        },
                    )

                print(
                    f"\r[DOWNLOAD] {Fore.LIGHTGREEN_EX}Successfully switched to{Style.RESET_ALL}: "
                    f"{filename}"
                )
            else:
                raise Exception("Failed to load downloaded audio file")

        except Exception as e:
            print(f"\r[DOWNLOAD] {Fore.LIGHTRED_EX}Download failed{Style.RESET_ALL}")
            print(
                f"\r[DOWNLOAD] {Fore.LIGHTBLACK_EX}Continuing with current audio file "
                f"(no interruption){Style.RESET_ALL}"
            )

            # Publish download_failed state
            if hasattr(mqtt_client, "publish_download_state"):
                mqtt_client.publish_download_state(
                    DownloadState.DOWNLOAD_FAILED,
                    {
                        "error_message": str(e),
                        "failed_url": url,
                        "original_state": (
                            original_state.value
                            if "original_state" in locals()
                            else "unknown"
                        ),
                        "current_file": (
                            os.path.basename(self.current_file)
                            if self.current_file
                            else None
                        ),
                        "playback_interrupted": False,
                    },
                )

    def get_audio_directory_path(self, script_dir):
        """Get the full path to the audio directory"""
        return os.path.join(script_dir, self.audio_dir)

    def ensure_audio_directory(self, script_dir):
        """Ensure audio directory exists"""
        full_path = self.get_audio_directory_path(script_dir)
        os.makedirs(full_path, exist_ok=True)
        return full_path

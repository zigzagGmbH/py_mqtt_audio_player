"""
Audio Player with MQTT Control - Refactored Main Application

- Multi-channel audio playback with device selection
- Real-time keyboard controls (Start/Stop, Play/Pause, Loop, Volume)
- MQTT integration for remote control
- File download capabilities
- Auto-start configuration
- Position tracking and health monitoring

ONGOING IMPLEMENTATIONS:
    - DONE :
        - [Removed][Dynamic Controls] Loop, Pause, Reset, Start/Stop with keyboard shortcuts
        - [Dynamic Controls]Vol ctrl during playback with keyboard shortcuts
        - Load data from config
        - Audio output device configurator (to write to config)
        - Implement "seek" play head
        - Apply MQTT control (input controls and output features)
        - First Refactor ...
        - Keyboard handling cross platform
        - Publish more frequently audio position ...
        - Publish Audio Strength (level) when playing ...
        - Receive channel info before playback (modify player & add MQTT ctrl) ...
        - Receive and apply channel info during playback
        - log mechanics with auto archiving ...
        - Implement new req for "file Path for audio file access" too, alongside with file fetch from file server url
        - Implement repeat behavior via MQTT (only defined topic in shaker player config (currently) but a behavior implemented player class wise
"""

import sys
import threading
import time
from colorama import Fore, Style
import argparse

# Import refactored modules
from config.config_loader import load_config, get_player_settings, get_audio_paths
from config.simple_logger import setup_logging, cleanup_logging, enable_auto_logging
from player.utils import (
    find_audio_files,
    list_available_devices,
    confirm_selected_device,
)
from player.core import AudioPlayer
from player.file_manager import AudioFileManager
from mqtt.client import MQTTAudioClient
from input.keyboard import input_handler, print_controls_help


def parse_arguments():
    """Parse command line arguments. Currently used for passing custom config file."""
    parser = argparse.ArgumentParser(description="MQTT Audio Player")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to configuration file (default: config.yaml in project root)",
    )
    return parser.parse_args()


class AudioPlayerApp:
    """Main application class that orchestrates all components"""

    def __init__(self):
        self.player = None
        self.mqtt_client = None
        self.file_manager = None
        self.stop_event = threading.Event()
        self.threads = []

        # Configuration
        self.config = None
        self.player_settings = None
        self.paths = None

    def load_configuration(self, config_file=None):
        """Load and process configuration"""
        try:
            logging_config, paths_config, player_config, mqtt_config = load_config(
                config_file
            )

            self.config = {
                "logging": logging_config,
                "paths": paths_config,
                "player": player_config,
                "mqtt": mqtt_config,
            }

            # Logger config ...
            client_id = mqtt_config["client_id"]
            log_dir = paths_config.get("log_file_dir", "logs")
            setup_logging(client_id, log_dir, logging_config.get("max_size_mb", 1))
            enable_auto_logging()  # ** This makes ALL print statements also go to log file

            self.player_settings = get_player_settings(player_config)
            self.paths = get_audio_paths(paths_config)

            print(f"{Fore.GREEN}Configuration loaded successfully{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}Failed to load configuration: {e}{Style.RESET_ALL}")
            return False

    def setup_audio_system(self):
        """Setup audio devices and find audio files"""
        # Find audio files
        wav_files, audio_file_exists, full_audio_dir = find_audio_files(
            self.paths["audio_dir"]
        )
        if not audio_file_exists:
            return False, None, None

        # List and validate audio devices
        list_available_devices()

        device_info, device_index, target_channels, channel_mapping = (
            confirm_selected_device(
                device=self.player_settings["device_name"],
                target_channels=self.player_settings["channels"],
                channel_mapping=self.player_settings["channel_mask"],
            )
        )

        # Update player settings if device capabilities are different
        self.player_settings["channels"] = target_channels
        self.player_settings["channel_mask"] = channel_mapping

        print(
            f"\n{Fore.LIGHTMAGENTA_EX}Selected device:{Style.RESET_ALL}\n"
            f"\t{Fore.LIGHTBLUE_EX}ID:{Style.RESET_ALL} {device_index}\n"
            f"\t{Fore.LIGHTBLUE_EX}Name:{Style.RESET_ALL} {device_info['name']}\n"
        )

        return True, wav_files, full_audio_dir

    def create_components(self, wav_files, audio_dir):
        """Create and configure all application components"""
        # Create audio player
        self.player = AudioPlayer(
            device=self.player_settings["device_name"],
            volume_factor=self.player_settings["volume"],
            target_sample_rate=self.player_settings["sample_rate"],
            target_channels=self.player_settings["channels"],
            channel_mapping=self.player_settings["channel_mask"],
            audio_level_enabled=self.player_settings["audio_level_enabled"],
        )

        # Configure auto-start
        self.player.set_auto_start(self.player_settings["auto_start"])

        # Create file manager
        self.file_manager = AudioFileManager(
            audio_dir=audio_dir, auto_start_enabled=self.player_settings["auto_start"]
        )

        # Load initial audio file
        selected_wav_file = wav_files[0]
        self.file_manager.set_current_file(selected_wav_file)

        if not self.player.load_audio_file(selected_wav_file):
            print(f"{Fore.RED}Failed to load initial audio file{Style.RESET_ALL}")
            return False

        # Start audio stream
        if not self.player.start_stream():
            print(f"{Fore.RED}Failed to start audio stream{Style.RESET_ALL}")
            return False

        # Create MQTT client
        self.mqtt_client = MQTTAudioClient(
            mqtt_config=self.config["mqtt"],
            player=self.player,
            file_manager=self.file_manager,
        )

        # Setup MQTT client
        self.mqtt_client.setup_client(self.stop_event)

        return True

    def start_threads(self):
        """Start all background threads"""
        # TBT
        # # Input handler thread
        # input_thread = threading.Thread(
        #     target=input_handler, args=(self.player, self.stop_event)
        # )
        # input_thread.daemon = True
        # input_thread.start()
        # self.threads.append(input_thread)
        print(
            f"{Fore.YELLOW}[TEST] Keyboard input DISABLED - use Ctrl+C to quit{Style.RESET_ALL}"
        )
        # --

        # MQTT client thread
        mqtt_thread = threading.Thread(
            target=self.mqtt_client.connect_and_run, args=(self.stop_event,)
        )
        mqtt_thread.daemon = True
        mqtt_thread.start()
        self.threads.append(mqtt_thread)

        # NEW - MQTT Health monitoring thread
        # Watchdog thread
        watchdog_thread = threading.Thread(
            target=self._watchdog_monitor, args=(self.stop_event,)
        )
        watchdog_thread.daemon = True
        watchdog_thread.start()
        self.threads.append(watchdog_thread)
        # ---

        print(f"{Fore.GREEN}All background threads started{Style.RESET_ALL}")

    def print_startup_info(self):
        """Print application startup information"""
        client_id = self.config["mqtt"]["client_id"]
        auto_start_status = (
            "ENABLED" if self.player_settings["auto_start"] else "DISABLED"
        )

        print(
            f'{Fore.MAGENTA}"{client_id}" Audio Player with MQTT Control{Style.RESET_ALL}'
        )

        # TBT
        # print(
        #     f"{Fore.CYAN}Controls: S=Start/Stop, P=Play/Pause, L=Loop, Q=Quit{Style.RESET_ALL}"
        # )
        print(
            f"{Fore.CYAN}Controls: MQTT only (keyboard disabled for testing){Style.RESET_ALL}"
        )
        # --

        print(f"{Fore.YELLOW}Auto-start: {auto_start_status}{Style.RESET_ALL}\n")

        # TBT
        # print(f"{Fore.GREEN}Player ready! Use keyboard controls:{Style.RESET_ALL}")
        # print_controls_help()
        # --

        print(f"{Fore.GREEN}Player ready! Use MQTT or Ctrl+C to quit{Style.RESET_ALL}")
        print()

    def run(self, config_file=None):
        """Main application run method"""
        print(f"{Fore.CYAN}Starting Audio Player Application...{Style.RESET_ALL}\n")

        # Load configuration with optional config file
        if not self.load_configuration(config_file):
            return 1

        # Setup audio system
        success, wav_files, audio_dir = self.setup_audio_system()
        if not success:
            return 1

        # Create components
        if not self.create_components(wav_files, audio_dir):
            return 1

        # Print startup information
        self.print_startup_info()

        # Start background threads
        self.start_threads()

        try:
            # Main event loop
            while not self.stop_event.is_set():
                time.sleep(0.1)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Received interrupt signal{Style.RESET_ALL}")
            self.stop_event.set()

        # Cleanup
        self.shutdown()
        return 0

    def shutdown(self):
        """Clean shutdown procedure"""
        print(f"\n{Fore.YELLOW}Shutting down...{Style.RESET_ALL}")

        # Stop audio stream
        if self.player:
            self.player.stop_stream()

        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=1.0)

        cleanup_logging()

        print(f"{Fore.GREEN}Goodbye!{Style.RESET_ALL}")

    # NEW - Watchdog monitor for MQTT health
    def _watchdog_monitor(self, stop_event):
        """Monitor system health and detect issues"""
        start_time = time.time()
        watchdog_interval = 30  # seconds

        while not stop_event.is_set():
            try:
                time.sleep(watchdog_interval)

                # Calculate uptime
                uptime_minutes = int(time.time() - start_time) // 60

                # Safety check: ensure mqtt_client exists
                if not self.mqtt_client:
                    print(f"{Fore.RED}[WATCHDOG] MQTT client not initialized!{Style.RESET_ALL}")
                    continue

                # Get health statuses
                mqtt_health = self.mqtt_client.get_health_status()
                active_threads = len([t for t in self.threads if t.is_alive()])
                threads_ok = (active_threads == len(self.threads))

                # Audio playback health check
                audio_health = "OK"
                audio_issues = []
                if hasattr(self, 'player') and self.player:
                    try:
                        health_status = self.player.check_playback_health()
                        if isinstance(health_status, dict) and not health_status.get('is_healthy', True):
                            audio_health = "STALLED"
                            audio_issues = health_status.get('issues', [])
                    except Exception as e:
                        audio_health = "ERROR"
                        audio_issues = [str(e)]

                # Build status string
                status = (
                    f"[WATCHDOG] Uptime:{uptime_minutes}m | "
                    f"MQTT:{'OK' if mqtt_health['connected'] else 'DOWN'} | "
                    f"Threads:{active_threads}/{len(self.threads)} | "
                    f"MsgRx:{mqtt_health['messages_rx']} | "
                    f"Audio:{audio_health}"
                )

                if audio_issues:
                    status += f" ({', '.join(audio_issues)})"

                # Color based on health
                if mqtt_health['connected'] and threads_ok and audio_health == "OK":
                    print(f"{Fore.GREEN}{status}{Style.RESET_ALL}")
                elif audio_health in ["STALLED", "ERROR"]:
                    print(f"{Fore.RED}{status} ⚠ AUDIO CALLBACK ISSUE!{Style.RESET_ALL}")
                elif not mqtt_health['connected']:
                    print(f"{Fore.RED}{status} ⚠ MQTT DOWN!{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}{status}{Style.RESET_ALL}")

            except Exception as e:
                print(f"{Fore.RED}[WATCHDOG] Error: {e}{Style.RESET_ALL}")


def main():
    """Application entry point"""

    # Parse command line arguments
    args = parse_arguments()

    app = AudioPlayerApp()

    try:
        # Pass config file argument to load_configuration
        return app.run(config_file=args.config)
    except KeyboardInterrupt:
        print(
            f"\n{Fore.YELLOW}Process interrupted by user. Exiting...{Style.RESET_ALL}"
        )
        return 0
    except Exception as e:
        print(f"{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
MQTT client for audio player with command handling and state publishing.
"""

import os
import json
import time
import threading
import paho.mqtt.client as mqtt
from colorama import Fore, Style


class DownloadState:
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    DOWNLOAD_FAILED = "download_failed"
    REVERTED = "reverted"


class MQTTAudioClient:
    def __init__(self, mqtt_config, player, file_manager=None):
        self.config = mqtt_config
        self.player = player
        self.file_manager = file_manager
        self.client = None
        self.health_thread = None
        self.position_thread = None
        self.level_thread = None
        # NEW
        # Health monitoring counters
        self.messages_received = 0
        self.messages_sent = 0
        self.last_message_time = time.time()


    def setup_client(self, stop_event):
        """Setup and configure MQTT client"""
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_message = self._on_message

        # Enable automatic reconnection
        self.client.reconnect_delay_set(min_delay=2, max_delay=5)

        # Set player's MQTT client
        self.player.set_mqtt_client(self.client)
        self.player._mqtt_config = self.config # For access in player

        # Pass stop_event through userdata
        self.client.user_data_set(stop_event)

        return self.client

    def connect_and_run(self, stop_event):
        """Connect to MQTT broker and run main loop"""
        try:
            self.client.connect(host=self.config["broker"], port=self.config["port"])
            print(
                f"\r[MQTT] {Fore.LIGHTBLUE_EX}Attempting connection to{Style.RESET_ALL} "
                f"mqtt://{self.config['broker']}:{self.config['port']}"
            )
        except Exception as e:
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Initial connection failed:{Style.RESET_ALL}"
            )
            print(
                f"\r[MQTT] {Fore.LIGHTBLACK_EX}Will keep trying to connect in background...{Style.RESET_ALL}"
            )

        # Start background loop
        self.client.loop_start()

        # Wait for stop signal
        while not stop_event.is_set():
            time.sleep(0.1)

        # Clean shutdown
        self._shutdown()

    def _shutdown(self):
        """Clean shutdown procedure"""
        try:
            health_topic = self.config["pub"]["topics"]["player_health"]
            offline_payload = {
                "status": "offline",
                "client_id": self.config["client_id"],
            }
            self.client.publish(health_topic, json.dumps(offline_payload))
            time.sleep(0.5)
            print(
                f"\r[MQTT] {Fore.LIGHTMAGENTA_EX}Offline status sent{Style.RESET_ALL}"
            )
        except Exception:
            pass

        print(f"\r[MQTT] {Fore.LIGHTBLACK_EX}Shutting down...{Style.RESET_ALL}")
        self.client.loop_stop()
        try:
            self.client.disconnect()
        except Exception:
            pass

    def _on_connect_fail(self, client, userdata):
        print(
            f"\r[MQTT] {Fore.LIGHTRED_EX}Connection failed - "
            f"{Fore.LIGHTYELLOW_EX}will retry automatically{Style.RESET_ALL}"
        )

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Lost connection:{Style.RESET_ALL} "
                f"{reason_code} - {Fore.LIGHTYELLOW_EX}reconnecting...{Style.RESET_ALL}"
            )
        else:
            print(f"\r[MQTT] {Fore.LIGHTCYAN_EX}Disconnected cleanly{Style.RESET_ALL}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        stop_event = userdata

        if reason_code.is_failure:
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Failed to connect{Style.RESET_ALL}: {reason_code}"
            )
        else:
            print(
                f"\r[MQTT] {Fore.LIGHTGREEN_EX}Connected{Style.RESET_ALL} to "
                f"mqtt://{self.config['broker']}:{self.config['port']}"
            )
            print(
                f"\r[MQTT] {Fore.LIGHTBLUE_EX}Subscribing to topics:{Style.RESET_ALL}"
            )

            # Subscribe to topics
            sub_topics = self.config["sub"]["topics"]
            for topic_name, topic_value in sub_topics.items():
                client.subscribe(topic_value)
                print(
                    f'\r           {Fore.LIGHTCYAN_EX}{topic_name}{Style.RESET_ALL}:"{topic_value}"'
                )

            print(f"\r[MQTT] {Fore.LIGHTGREEN_EX}Setup complete{Style.RESET_ALL}")

            # Start health monitoring
            self._start_health_monitoring(client, stop_event)

            # Start position monitoring
            self._start_position_monitoring(client, stop_event)

            # Start level monitoring
            self._start_level_monitoring(client, stop_event)
            
            # Initialize state tracking and publish initial state
            self.player._last_published_state = None  # Force Publish
            self.player.publish_player_state()
            print(f"\r[MQTT] {Fore.LIGHTGREEN_EX}Initial state published{Style.RESET_ALL}")

    def _start_health_monitoring(self, client, stop_event):
        """Start health publisher thread"""
        heartbeat_enabled = self.config.get("heartbeat", False)
        if isinstance(heartbeat_enabled, str):
            heartbeat_enabled = heartbeat_enabled.upper() in ["TRUE", "1", "YES", "ON"]

        if heartbeat_enabled:
            if self.health_thread is None or not self.health_thread.is_alive():
                self.health_thread = threading.Thread(
                    target=self._health_publisher, args=(client, stop_event)
                )
                self.health_thread.daemon = True
                self.health_thread.start()
                print(
                    f"\r[MQTT] {Fore.LIGHTMAGENTA_EX}Health monitoring started{Style.RESET_ALL}"
                )
        else:
            print(
                f"\r[MQTT] {Fore.LIGHTMAGENTA_EX}Health monitoring disabled in config{Style.RESET_ALL}"
            )

    def _start_position_monitoring(self, client, stop_event):
        """Start position publisher thread"""
        if self.position_thread is None or not self.position_thread.is_alive():
            self.position_thread = threading.Thread(
                target=self._position_publisher, args=(client, stop_event)
            )
            self.position_thread.daemon = True
            self.position_thread.start()
            print(
                f"\r[MQTT] {Fore.LIGHTCYAN_EX}Position publisher started{Style.RESET_ALL}"
            )

    def _health_publisher(self, client, stop_event):
        """Publish health status periodically"""
        health_topic = self.config["pub"]["topics"]["player_health"]
        heartbeat_freq = self.config["heartbeat_freq"]

        while not stop_event.is_set():
            try:
                payload = {
                    "status": "online",
                    "client_id": self.config["client_id"],
                }
                client.publish(health_topic, json.dumps(payload))
            except Exception as e:
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Health publish error: {e}{Style.RESET_ALL}"
                )

            time.sleep(heartbeat_freq)

    def _start_level_monitoring(self, client, stop_event):
        """Start audio level publisher thread"""
        # Check if level monitoring is enabled
        level_enabled = getattr(self.player, "audio_level_enabled", False)

        if level_enabled:
            if self.level_thread is None or not self.level_thread.is_alive():
                self.level_thread = threading.Thread(
                    target=self._level_publisher, args=(client, stop_event)
                )
                self.level_thread.daemon = True
                self.level_thread.start()
                print(
                    f"\r[MQTT] {Fore.LIGHTGREEN_EX}Level publisher started{Style.RESET_ALL}"
                )
        else:
            print(
                f"\r[MQTT] {Fore.LIGHTMAGENTA_EX}Level publishing disabled in config{Style.RESET_ALL}"
            )

    def _position_publisher(self, client, stop_event):
        """Publish playhead position during playback"""
        position_topic = self.config["pub"]["topics"]["audio_position"]

        while not stop_event.is_set():
            try:
                if (
                    self.player.state.value == "playing"
                    and self.player.audio_length > 0
                ):

                    position_samples = self.player.position
                    total_samples = self.player.audio_length
                    percentage = (
                        (position_samples / total_samples) * 100
                        if total_samples > 0
                        else 0
                    )

                    position_data = {
                        "position": self.player.get_time_string(position_samples),
                        "total_duration": self.player.get_total_time_string(),
                        "percentage": round(percentage, 1),
                        "current_file": (
                            os.path.basename(self.file_manager.current_file)
                            if self.file_manager and self.file_manager.current_file
                            else None
                        ),
                    }

                    client.publish(
                        position_topic, json.dumps(position_data), retain=True
                    )

            except Exception as e:
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Position publish error: {e}{Style.RESET_ALL}"
                )

            time.sleep(0.125)  # 8 times per second

    def _level_publisher(self, client, stop_event):
        """Publish audio levels during playback"""
        level_topic = self.config["pub"]["topics"]["audio_level"]
        level_freq = self.config.get(
            "audio_level_freq", 10
        )  # Get from config, or else 10 Hz (1/10 sec)

        while not stop_event.is_set():
            try:
                if self.player.state.value == "playing":
                    level_data = {
                        "level": round(self.player.normalized_audio_level, 4),
                        "timestamp": time.time(),
                    }
                    client.publish(level_topic, json.dumps(level_data))

            except Exception as e:
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Level publish error: {e}{Style.RESET_ALL}"
                )

            time.sleep(1.0 / level_freq)  # Use configurable frequency

    def _on_message(self, client, userdata, message):
        """Handle incoming MQTT messages"""
        topic = message.topic
        
        # NEW for monitoring 
        self.messages_received += 1
        self.last_message_time = time.time()
        # ----
        
        payload = message.payload.decode().strip()
        print(
            f"\r[MQTT] -->> TOPIC: {Fore.LIGHTMAGENTA_EX}{topic}{Style.RESET_ALL} "
            f"and PAYLOAD: {Fore.LIGHTCYAN_EX}{payload}{Style.RESET_ALL}"
        )

        try:
            # Route messages to appropriate handlers
            if topic == self.config["sub"]["topics"]["file_topic"]:
                self._handle_file_download(payload)
            elif topic == self.config["sub"]["topics"]["play_pause_cmd_topic"]:
                self._handle_play_pause_command(payload)
            elif topic == self.config["sub"]["topics"]["start_stop_cmd_topic"]:
                self._handle_start_stop_command(payload)
            elif topic == self.config["sub"]["topics"]["loop_toggle_cmd_topic"]:
                self._handle_loop_command(payload)
            elif topic == self.config["sub"]["topics"]["volume_cmd_topic"]:
                self._handle_volume_command(payload)
            elif topic == self.config["sub"]["topics"]["seek_cmd_topic"]:
                self._handle_seek_command(payload)
            elif topic == self.config["sub"]["topics"]["status_check"]:
                self._handle_status_request(payload)
            elif topic == self.config["sub"]["topics"]["channel_mask_cmd_topic"]:
                self._handle_channel_mask_command(payload)
            elif topic == self.config["sub"]["topics"]["repeat_cmd_topic"]:
                self._handle_repeat_command(payload)
            else:
                print(f"\r[MQTT] ⚠ Unknown topic: {topic}")

        except Exception as e:
            print(f"\r[MQTT] Command processing error: {e}")

    def _handle_channel_mask_command(self, payload):
        """Handle channel mask commands"""
        try:
            # Parse JSON array from payload
            channel_mask = json.loads(payload)

            # Validate it's a list
            if not isinstance(channel_mask, list):
                print(
                    f"\r[MQTT] Invalid channel mask format: expected list, got {type(channel_mask)}"
                )
                return

            print(f"\r[MQTT] Received channel mask: {channel_mask}")

            # Send to AudioPlayer for validation and setting
            if self.player.set_dynamic_channel_mask(channel_mask):
                print(f"\r[MQTT] Channel mask applied: {channel_mask}")
            else:
                print(f"\r[MQTT] Channel mask rejected: {channel_mask}")

        except json.JSONDecodeError as e:
            print(f"\r[MQTT] Invalid JSON in channel mask payload: {payload}")
            print("\r[MQTT] JSON Error")
        except Exception as e:
            print(f"\r[MQTT] Channel mask processing error: {e}")
            print(f"\r[MQTT] Payload was: {payload}")

    def _handle_repeat_command(self, payload):
        """Handle repeat playback commands"""
        try:
            # Parse JSON payload
            repeat_data = json.loads(payload)
            
            # Extract parameters
            count = int(repeat_data.get("count", 1))
            interval = float(repeat_data.get("interval", 0.0))
            
            # Check for cancellation (count=0)
            if count == 0:
                self.player.cancel_repeat()
                print(f"\r[MQTT] Repeat cancelled via count=0")
                return
            
            # Validation: count must be 1-10
            MAX_REPEAT_COUNT = 10
            if not (1 <= count <= MAX_REPEAT_COUNT):
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid repeat count:{Style.RESET_ALL} "
                    f"{count} (must be 1-{MAX_REPEAT_COUNT})"
                )
                return
            
            # Validation: interval must be 0-30 seconds
            MAX_REPEAT_INTERVAL = 30.0
            if not (0 <= interval <= MAX_REPEAT_INTERVAL):
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid repeat interval:{Style.RESET_ALL} "
                    f"{interval}s (must be 0-{MAX_REPEAT_INTERVAL})"
                )
                return
            
            # Start repeat playback
            print(
                f"\r[MQTT] Starting repeat: {count}x with {interval}s interval"
            )
            self.player.start_repeat_playback(count, interval)
            
        except json.JSONDecodeError:
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid JSON in repeat payload:{Style.RESET_ALL} {payload}"
            )
        except (ValueError, KeyError) as e:
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid repeat command:{Style.RESET_ALL} {e}"
            )
            print(f"\r[MQTT] Payload was: {payload}")
        except Exception as e:
            print(f"\r[MQTT] Repeat command processing error: {e}")
    
    def _handle_file_download(self, payload):
        """Handle file download requests"""
        try:
            # Try JSON first
            url_data = json.loads(payload)
            url = url_data.get("url") or url_data.get("audio_url") or str(url_data)
        except json.JSONDecodeError:
            # Fallback to direct URL string
            url = payload

        # Handle both URLs and absolute paths
        if url and url.startswith(("http://", "https://")):
            print(f"\r[MQTT] Received download request: {url}")
        elif url:  # Could be an absolute file path
            print(f"\r[MQTT] Received file path request: {url}")
        else:
            print(f"\r[MQTT] Empty payload received")
            return

        # Start processing in thread (works for both URLs and paths)
        if self.file_manager:
            download_thread = threading.Thread(
                target=self.file_manager.download_audio_file,
                args=(url, self.client, self.player),
            )
            download_thread.daemon = True
            download_thread.start()
        else:
            print("\r[MQTT] No file manager available")

    def _handle_play_pause_command(self, payload):
        """Handle play/pause commands"""
        command = payload.lower().strip()
        if command in ["play", "start"]:
            if self.player.state.value == "stopped":
                self.player.start_playback()
                print("\r[MQTT] Start command executed")
            else:
                self.player.send_command("play")
                print("\r[MQTT] Play command executed")
        elif command == "pause":
            self.player.send_command("pause")
            print("\r[MQTT] ⏸ Pause command executed")

    def _handle_start_stop_command(self, payload):
        """Handle start/stop commands"""
        command = payload.lower().strip()
        if command in ["start", "play"]:
            self.player.start_playback()
            print("\r[MQTT] Start command executed")
        elif command == "stop":
            # STICKY BEHAVIOR: Stop does NOT cancel repeat/loop params
            # Just stop playback and cancel the worker thread if waiting
            self.player.stop_playback()
            
            # Cancel the worker thread if it's waiting between plays
            if self.player.repeat_thread and self.player.repeat_thread.is_alive():
                self.player.repeat_cancel_event.set()
                self.player.repeat_thread.join(timeout=0.5)
                # Reset worker thread reference
                self.player.repeat_thread = None
                # Reset counter (repeat params stay active)
                with self.player.repeat_params_lock:
                    self.player.repeat_current = 0
            
            print("\r[MQTT] Stop command executed (repeat/loop params preserved)")

    def _handle_loop_command(self, payload):
        """Handle loop toggle commands"""
        if isinstance(payload, bool):
            loop_enabled = payload
        else:
            payload_str = str(payload).lower().strip()
            loop_enabled = payload_str in ["true", "1", "yes", "on", "enable"]

        # Update loop state regardless of repeat mode
        old_loop = self.player.loop_enabled
        self.player.loop_enabled = loop_enabled
        
        # Publish state change immediately
        if old_loop != loop_enabled:
            self.player.check_and_publish_state_changes()
        
        loop_status = "ENABLED" if loop_enabled else "DISABLED"
        
        # If repeat is active, note that loop will take over after current play
        if self.player.repeat_enabled and loop_enabled:
            print(f"\r[MQTT] Loop {loop_status} (will take effect after current play ends)")
        else:
            print(f"\r[MQTT] Loop: {loop_status}")

    def _handle_volume_command(self, payload):
        """Handle volume commands"""
        payload_str = str(payload).strip()

        if payload_str.startswith("+"):
            self.player.volume_up()
            print(f"\r[MQTT] Volume up: {self.player.get_volume_percentage()}%")
        elif payload_str.startswith("-"):
            self.player.volume_down()
            print(f"\r[MQTT] 🔉 Volume down: {self.player.get_volume_percentage()}%")
        else:
            try:
                volume_value = float(payload_str)
                if 0.0 <= volume_value <= 1.0:
                    old_volume = self.player.current_volume_factor
                    self.player.current_volume_factor = round(volume_value, 2)
                    if old_volume != self.player.current_volume_factor:
                        self.player.check_and_publish_state_changes()
                    print(
                        f"\r[MQTT] Volume set: {self.player.get_volume_percentage()}%"
                    )
            except ValueError:
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid volume value:{Style.RESET_ALL} {payload}"
                )

    def _handle_seek_command(self, payload):
        """Handle seek commands"""
        # payload_str = str(payload).strip()
        payload_str = str(payload).strip().strip('"').strip("'")

        try:
            # Parse time format (MM:SS or seconds)
            if ":" in payload_str:
                parts = payload_str.split(":")
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    target_seconds = minutes * 60 + seconds
                else:
                    print(
                        f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid seek format{Style.RESET_ALL}"
                    )
                    return
            elif payload_str.endswith("%"):
                percentage = float(payload_str[:-1])  # Remove % and convert
                # print(f"\r[DEBUG] percentage: {percentage}")
                if 0 <= percentage <= 100 and self.player.audio_length > 0:
                    total_duration_seconds = (
                        self.player.audio_length / self.player.target_sample_rate
                    )
                    target_seconds = (percentage / 100.0) * total_duration_seconds
                else:
                    print(
                        f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid percentage:{Style.RESET_ALL} {payload}"
                    )
                    return
            else:
                target_seconds = float(payload_str)

            if self.player.seek_to_time(target_seconds):
                target_time = self.player.get_time_string(self.player.position)
                print(f"\r[MQTT] ⏭ Jumped to: {target_time}")
            else:
                total_time = self.player.get_total_time_string()
                print(
                    f"\r[MQTT] {Fore.LIGHTRED_EX}Seek position out of range. Max:{Style.RESET_ALL} {total_time}"
                )

        except (ValueError, TypeError):
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Invalid seek command:{Style.RESET_ALL} {payload}"
            )

    def _handle_status_request(self, payload):
        """Handle status check requests"""
        print("\r[MQTT] Status request received")
        self.player.publish_player_state()

        # Also publish position if playing
        if self.player.state.value == "playing":
            position_topic = self.config["pub"]["topics"]["audio_position"]
            position_samples = self.player.position
            total_samples = self.player.audio_length
            percentage = (
                (position_samples / total_samples) * 100 if total_samples > 0 else 0
            )

            position_data = {
                "position": self.player.get_time_string(position_samples),
                "total_duration": self.player.get_total_time_string(),
                "percentage": round(percentage, 1),
            }
            self.client.publish(position_topic, json.dumps(position_data), retain=True)

    def publish_download_state(self, download_state, additional_info=None):
        """Publish download state updates"""
        try:
            status_topic = self.config["pub"]["topics"]["player_status"]
            state_data = {"download_state": download_state, "timestamp": time.time()}

            if hasattr(self.player, "state"):
                state_data.update(
                    {
                        "player_state": self.player.state.value,
                        "loop_enabled": self.player.loop_enabled,
                        "volume": round(self.player.current_volume_factor, 2),
                        "volume_percentage": self.player.get_volume_percentage(),
                        "auto_start": self.player.auto_start_enabled,
                    }
                )

                if self.player.audio_length > 0:
                    state_data.update(
                        {
                            "position": self.player.get_time_string(
                                self.player.position
                            ),
                            "total_duration": self.player.get_total_time_string(),
                        }
                    )

            if additional_info:
                state_data.update(additional_info)

            self.client.publish(status_topic, json.dumps(state_data))
            print(f"\r[MQTT] >>> Download state: {download_state}")

        except Exception as e:
            print(
                f"\r[MQTT] {Fore.LIGHTRED_EX}Download state publish error: {e}{Style.RESET_ALL}"
            )
    
    def get_health_status(self):
        """Get health status for watchdog"""
        try:
            is_connected = self.client.is_connected() if self.client else False
            return {
                "connected": is_connected,
                "messages_rx": self.messages_received,
                "last_activity": time.time() - self.last_message_time
            }
        except Exception:
            return {"connected": False, "messages_rx": 0, "last_activity": 999}

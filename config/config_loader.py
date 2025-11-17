"""
Configuration loading and management module.
Handles YAML config loading with Jinja2 templating.
"""

import yaml
from jinja2 import Template
from pathlib import Path

def load_config(config_file=None):
    """
    Load and process configuration file with Jinja2 templating.
    Args:
        config_file: Path to config file. If None, uses default "config.yaml"
                    in project root directory.
    Returns:
        tuple: (logging_config, paths_config, player_config, mqtt_config)
    """
    
    if config_file is None:
        # Use project root's config.yaml
        script_dir = Path(__file__).parent
        config_file = script_dir.parent / "config.yaml"
    else:
        # Use user provided config file path
        config_file = Path(config_file)
        
        # Validate the file exists
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
    with open(config_file, "r") as file:
        config_str = file.read()

    config_unrendered = yaml.safe_load(config_str)

    # Extract basic configs
    logging_config = config_unrendered["logging"]
    paths_config = config_unrendered["paths"]
    player_config = config_unrendered["player"]

    # Process MQTT config with Jinja2 templating
    mqtt_template = Template(config_str)
    rendered_mqtt_info = mqtt_template.render(mqtt=config_unrendered["mqtt"])
    mqtt_config = yaml.safe_load(rendered_mqtt_info)["mqtt"]

    return logging_config, paths_config, player_config, mqtt_config


def _parse_boolean_config(value):
    """Parse boolean from config (handles strings like 'True', 'False')"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.upper() in ["TRUE", "1", "YES", "ON"]
    return bool(value)


def get_player_settings(player_config):
    """
    Extract player-specific settings from config.
    Returns:
        dict: Player configuration parameters
    """
    return {
        "device_name": player_config["device_name"],
        "sample_rate": player_config["device_sample_rate"],
        "volume": player_config["playback_volume_factor"],
        "channels": player_config["device_channels"],
        "channel_mask": player_config["playback_channel_mask"],
        "auto_start": _parse_boolean_config(player_config.get("auto_start", False)),
        "audio_level_enabled": _parse_boolean_config(
            player_config.get("audio_level_enabled", False)
        ),
    }


def get_audio_paths(paths_config):
    """
    Get audio-related paths from config.
    Returns:
        dict: Path configuration
    """
    return {
        "audio_dir": paths_config["audio_file_dir"],
        "log_dir": paths_config["log_file_dir"],
    }
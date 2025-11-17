#!/usr/bin/env python3
"""
Interactive Sound Device Configurator

This script helps configure audio playback devices and updates the config.yaml file.
It only shows output devices and guides the user through the configuration process.
"""

import sounddevice as sd
import yaml
import sys
import copy
import subprocess
from pathlib import Path

# Try to import colorama for colored output
try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    color_support = True
except ImportError:
    # Create dummy color class if colorama isn't available
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = DummyColor()
    Style = DummyColor()
    color_support = False


def print_header(title, width=80):
    """Print a formatted header"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}" + "=" * width + Style.RESET_ALL)
    print(f"{Fore.CYAN}{Style.BRIGHT} {title} {Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}" + "=" * width + Style.RESET_ALL)


def print_section(title, width=80):
    """Print a formatted section header"""
    print(f"\n{Fore.YELLOW}{Style.BRIGHT} {title} {Style.RESET_ALL}")
    print(f"{Fore.YELLOW}" + "-" * width + Style.RESET_ALL)


def get_output_devices():
    """Get all available output audio devices"""
    devices = sd.query_devices()
    output_devices = []
    
    try:
        default_output = sd.query_devices(kind="output")
        default_index = default_output['index']
    except Exception:
        default_index = None
    
    for i, device in enumerate(devices):
        if device["max_output_channels"] > 0:
            is_default = (i == default_index)
            output_devices.append({
                'index': i,
                'name': device['name'],
                'channels': device['max_output_channels'],
                'sample_rate': int(device['default_samplerate']),
                'is_default': is_default,
                'device_info': device
            })
    
    return output_devices


def display_output_devices(output_devices):
    """Display all output devices in a formatted way"""
    print_section("Available Audio Output Devices")
    
    for device in output_devices:
        default_marker = f" {Fore.GREEN}(DEFAULT){Style.RESET_ALL}" if device['is_default'] else ""
        
        print(f"\n{Fore.BLUE}{Style.BRIGHT}Device {device['index']}: {Fore.WHITE}{device['name']}{Style.RESET_ALL}{default_marker}")
        print(f"  Channels:     {Fore.GREEN}{device['channels']}{Style.RESET_ALL} out")
        print(f"  Sample Rate:  {Fore.GREEN}{device['sample_rate']} Hz{Style.RESET_ALL}")
        
        # Show latency info if available
        device_info = device['device_info']
        if device_info['max_output_channels'] > 0:
            print(f"  Output Latency: {Fore.GREEN}{device_info['default_low_output_latency'] * 1000:.2f}{Style.RESET_ALL} ms (low), "
                  f"{Fore.GREEN}{device_info['default_high_output_latency'] * 1000:.2f}{Style.RESET_ALL} ms (high)")


def get_yes_no_input(prompt, default=None):
    """Get yes/no input from user with validation"""
    while True:
        if default:
            prompt_text = f"{prompt} (default: {default}): "
        else:
            prompt_text = f"{prompt} (y/n): "
        
        user_input = input(prompt_text).strip().lower()
        
        if not user_input and default:
            return default.lower() == 'y'
        
        if user_input in ['y', 'yes', 'true', '1']:
            return True
        elif user_input in ['n', 'no', 'false', '0']:
            return False
        else:
            print(f"{Fore.RED}Please enter 'y' for yes or 'n' for no.{Style.RESET_ALL}")


def get_device_selection(output_devices):
    """Get device selection from user with validation"""
    device_indices = [device['index'] for device in output_devices]
    
    while True:
        try:
            print(f"\n{Fore.YELLOW}Available device IDs: {device_indices}{Style.RESET_ALL}")
            user_input = input("Enter the device ID you want to use: ").strip()
            
            device_id = int(user_input)
            
            if device_id in device_indices:
                # Find the device with this index
                for device in output_devices:
                    if device['index'] == device_id:
                        return device
            else:
                print(f"{Fore.RED}Invalid device ID. Please choose from: {device_indices}{Style.RESET_ALL}")
                
        except ValueError:
            print(f"{Fore.RED}Please enter a valid number.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Configuration cancelled by user.{Style.RESET_ALL}")
            sys.exit(0)


def configure_channel_mask(total_channels):
    """Configure channel mask by asking user for each channel"""
    print(f"\n{Fore.YELLOW}Channel Configuration{Style.RESET_ALL}")
    print(f"The selected device has {total_channels} output channels.")
    print("For each channel, choose whether to enable (y) or disable (n) audio output.")
    print(f"{Fore.CYAN}Channel numbering starts from 1.{Style.RESET_ALL}")
    
    channel_mask = []
    
    for i in range(total_channels):
        channel_num = i + 1
        while True:
            try:
                enable = get_yes_no_input(f"Enable Channel {channel_num}")
                channel_mask.append(1 if enable else 0)
                break
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Configuration cancelled by user.{Style.RESET_ALL}")
                sys.exit(0)
    
    # Validate that at least one channel is enabled
    if sum(channel_mask) == 0:
        print(f"{Fore.YELLOW}Warning: No channels enabled. Enabling channel 1 by default.{Style.RESET_ALL}")
        channel_mask[0] = 1
    
    return channel_mask


def load_config():
    """Load current configuration from config.yaml"""
    # config_path = Path("config.yaml")
     # Get the script's directory and go one level up where the config file is ...
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config.yaml"
    
    if not config_path.exists():
        print(f"{Fore.RED}Error: config.yaml not found in current directory.{Style.RESET_ALL}")
        print("Please run this script from the project root directory.")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"{Fore.RED}Error loading config.yaml: {e}{Style.RESET_ALL}")
        sys.exit(1)


def save_config(config):
    """Save updated configuration to config.yaml"""
    # config_path = Path("config.yaml")
    # Get the script's directory and go one level up where the config file is ...
    script_dir = Path(__file__).parent
    config_path = script_dir.parent / "config.yaml"
    
    try:
        # Create backup
        backup_path = config_path.with_suffix('.yaml.backup')
        if config_path.exists():
            with open(config_path, 'r') as src, open(backup_path, 'w') as dst:
                dst.write(src.read())
            print(f"{Fore.GREEN}Backup created: {backup_path}{Style.RESET_ALL}")
        
        # Save new config with custom formatting for channel mask
        with open(config_path, 'w') as file:
            # Use a custom representor to format lists in flow style
            def represent_list(dumper, data):
                # Check if this is the channel mask (contains only 0s and 1s)
                if all(isinstance(x, int) and x in [0, 1] for x in data):
                    return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
                return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=False)
            
            yaml.add_representer(list, represent_list)
            yaml.dump(config, file, default_flow_style=False, indent=2)
        
        print(f"{Fore.GREEN}Configuration saved successfully to {config_path}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error saving config.yaml: {e}{Style.RESET_ALL}")
        sys.exit(1)


def display_configuration_summary(old_config, new_config):
    """Display summary of configuration changes"""
    print_section("Configuration Summary")
    
    old_player = old_config.get('player', {})
    new_player = new_config.get('player', {})
    
    changes = []
    
    # Check each field for changes
    fields_to_check = ['device_name', 'device_sample_rate', 'device_channels', 'playback_channel_mask']
    
    for field in fields_to_check:
        old_value = old_player.get(field, 'Not set')
        new_value = new_player.get(field, 'Not set')
        
        if old_value != new_value:
            changes.append((field, old_value, new_value))
    
    if changes:
        print(f"\n{Fore.GREEN}The following changes will be made:{Style.RESET_ALL}")
        for field, old_val, new_val in changes:
            print(f"  {Fore.YELLOW}{field}:{Style.RESET_ALL}")
            print(f"    Old: {Fore.RED}{old_val}{Style.RESET_ALL}")
            print(f"    New: {Fore.GREEN}{new_val}{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.YELLOW}No changes detected.{Style.RESET_ALL}")
    
    # Show active channels in a readable format
    if 'playback_channel_mask' in new_player:
        mask = new_player['playback_channel_mask']
        active_channels = [i + 1 for i, enabled in enumerate(mask) if enabled]
        print(f"\n{Fore.CYAN}Active Channels: {active_channels} (out of {len(mask)} total){Style.RESET_ALL}")


def run_test_script():
    """Run the audio device test script and display its output"""
    script_dir = Path(__file__).parent
    test_script = script_dir / "02_test_sound_device.py"
    
    # Check if the test script exists
    if not Path(test_script).exists():
        print(f"{Fore.RED}Error: {test_script} not found in current directory.{Style.RESET_ALL}")
        return
    
    try:
        print(f"{Fore.YELLOW}" + "=" * 60 + f"{Style.RESET_ALL}")
        print(f"{Fore.YELLOW} Running: {test_script} {Style.RESET_ALL}")
        print(f"{Fore.YELLOW}" + "=" * 60 + f"{Style.RESET_ALL}")
        
        # Run the script and capture output in real-time
        process = subprocess.Popen(
            [sys.executable, test_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Print output line by line as it comes
        for line in process.stdout:
            print(line, end='')
        
        # Wait for the process to complete
        return_code = process.wait()
        
        print(f"\n{Fore.YELLOW}" + "=" * 60 + f"{Style.RESET_ALL}")
        
        if return_code == 0:
            print(f"{Fore.GREEN}✓ Test completed successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠ Test completed with return code: {return_code}{Style.RESET_ALL}")
            
    except subprocess.SubprocessError as e:
        print(f"{Fore.RED}Error running test script: {e}{Style.RESET_ALL}")
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Test interrupted by user.{Style.RESET_ALL}")
        try:
            process.terminate()
        except (ProcessLookupError, PermissionError, OSError):
            # Process might have already terminated or we don't have permission
            pass
    except Exception as e:
        print(f"{Fore.RED}Unexpected error running test: {e}{Style.RESET_ALL}")


def main():
    """Main configuration function"""
    print_header("Interactive Sound Device Configurator")
    
    # Get available output devices
    output_devices = get_output_devices()
    
    if not output_devices:
        print(f"{Fore.RED}No output audio devices found!{Style.RESET_ALL}")
        sys.exit(1)
    
    # Display available devices
    display_output_devices(output_devices)
    
    # Ask if user wants to configure
    print(f"\n{Fore.WHITE}This tool will help you configure your audio playback device.{Style.RESET_ALL}")
    
    try:
        configure = get_yes_no_input(f"\n{Fore.YELLOW}Do you want to configure the playback device?{Style.RESET_ALL}")
        
        if not configure:
            print(f"{Fore.YELLOW}Configuration cancelled. Exiting...{Style.RESET_ALL}")
            sys.exit(0)
        
        # Load current configuration
        print(f"\n{Fore.CYAN}Loading current configuration...{Style.RESET_ALL}")
        config = load_config()
        old_config = copy.deepcopy(config)  # Use deep copy to avoid reference issues
        
        # Get device selection
        print(f"\n{Fore.YELLOW}Step 1: Select Audio Device{Style.RESET_ALL}")
        selected_device = get_device_selection(output_devices)
        
        print(f"\n{Fore.GREEN}Selected device: {selected_device['name']} (ID: {selected_device['index']}){Style.RESET_ALL}")
        
        # Update configuration
        if 'player' not in config:
            config['player'] = {}
        
        # Update device name
        config['player']['device_name'] = selected_device['name']
        
        # Update sample rate automatically
        config['player']['device_sample_rate'] = selected_device['sample_rate']
        print(f"Auto-configured sample rate: {selected_device['sample_rate']} Hz")
        
        # Update channels automatically
        config['player']['device_channels'] = selected_device['channels']
        print(f"Auto-configured channels: {selected_device['channels']}")
        
        # Configure channel mask
        print(f"\n{Fore.YELLOW}Step 2: Configure Channel Mask{Style.RESET_ALL}")
        channel_mask = configure_channel_mask(selected_device['channels'])
        config['player']['playback_channel_mask'] = channel_mask
        
        # Display summary
        display_configuration_summary(old_config, config)
        
        # Confirm changes
        confirm = get_yes_no_input(f"\n{Fore.YELLOW}Save these changes to config.yaml?{Style.RESET_ALL}")
        
        if confirm:
            save_config(config)
            print(f"\n{Fore.GREEN}✓ Configuration completed successfully!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}You can now run your audio player with the new settings.{Style.RESET_ALL}")
            
            # Ask if user wants to test the configuration
            test_config = get_yes_no_input(f"\n{Fore.YELLOW}Do you want to test the new configuration now?{Style.RESET_ALL}")
            
            if test_config:
                print(f"\n{Fore.CYAN}Running audio device test...{Style.RESET_ALL}")
                run_test_script()
        else:
            print(f"{Fore.YELLOW}Changes not saved. Configuration cancelled.{Style.RESET_ALL}")
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Configuration interrupted by user. Exiting...{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
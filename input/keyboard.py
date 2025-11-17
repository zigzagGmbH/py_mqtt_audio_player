"""
Enhanced cross-platform keyboard input handling for audio player controls.
"""

import time
import sys
import atexit
from colorama import init, Fore, Style

# Initialize colorama for Windows ANSI support
init(autoreset=True)

# Cross-platform keyboard input handling
try:
    import msvcrt  # Windows
    WINDOWS = True
    UNIX = False
except ImportError:
    import select  # Unix/Linux/macOS
    import tty
    import termios
    WINDOWS = False
    UNIX = True


class KeyboardHandler:
    """Enhanced keyboard handler with proper terminal management"""
    
    def __init__(self):
        self.old_terminal_settings = None
        self.terminal_configured = False
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
    def setup_terminal(self):
        """Setup terminal for non-blocking input"""
        if UNIX and not self.terminal_configured:
            try:
                # Save current terminal settings
                self.old_terminal_settings = termios.tcgetattr(sys.stdin)
                
                # Set terminal to raw mode for immediate key detection
                tty.setraw(sys.stdin.fileno())
                self.terminal_configured = True
                
                # Also clear the screen and hide cursor for cleaner output
                print("\033[2J\033[H", end="")  # Clear screen and move to top
                print("\033[?25l", end="")       # Hide cursor
                sys.stdout.flush()
                
            except Exception as e:
                print(f"Warning: Could not configure terminal: {e}")
                
    def cleanup(self):
        """Restore terminal settings"""
        if UNIX and self.terminal_configured and self.old_terminal_settings:
            try:
                # Show cursor and restore terminal
                print("\033[?25h", end="")  # Show cursor
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_terminal_settings)
                self.terminal_configured = False
            except Exception:
                pass
                
    def get_keypress(self):
        """Enhanced cross-platform non-blocking keyboard input"""
        if WINDOWS:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                # Handle special keys
                if key == b'\xe0':  # Arrow keys and other special keys
                    key = msvcrt.getch()
                    return None  # Ignore special keys for now
                try:
                    return key.decode("utf-8").lower()
                except UnicodeDecodeError:
                    return None
        else:
            # Unix/Linux/macOS
            if select.select([sys.stdin], [], [], 0.01) == ([sys.stdin], [], []):
                try:
                    char = sys.stdin.read(1)
                    # Handle escape sequences (arrow keys, etc.)
                    if char == '\x1b':  # ESC sequence
                        # Read the next characters to handle arrow keys
                        if select.select([sys.stdin], [], [], 0.01) == ([sys.stdin], [], []):
                            char += sys.stdin.read(1)
                            if select.select([sys.stdin], [], [], 0.01) == ([sys.stdin], [], []):
                                char += sys.stdin.read(1)
                        return None  # Ignore escape sequences for now
                    return char.lower()
                except Exception:
                    return None
        return None


def clear_line():
    """Clear the current line for clean output"""
    print("\r\033[K", end="")


def print_status_line(status_text):
    """Print status line with proper clearing"""
    clear_line()
    print(f"\r{status_text}", end="")
    sys.stdout.flush()


def input_handler(player, stop_event):
    """Enhanced keyboard input handler with better terminal management"""
    keyboard = KeyboardHandler()
    
    try:
        keyboard.setup_terminal()
        
        # Print initial status
        print_status_line(player.get_status_line())
        
        last_status_update = time.time()
        
        while not stop_event.is_set():
            key = keyboard.get_keypress()
            
            if key:
                # Clear the current line before processing command
                clear_line()
                
                if key == "q":
                    print(f"\r{Fore.YELLOW}Quitting...{Style.RESET_ALL}")
                    stop_event.set()
                    break
                elif key == "s":
                    player.start_stop_toggle()
                elif key == "p":
                    player.play_pause_toggle()
                elif key == "l":
                    player.toggle_loop()
                elif key in ["+", "="]:  # + key (with or without shift)
                    player.volume_up()
                    print(f"\r{Fore.GREEN}Volume: {player.get_volume_percentage()}%{Style.RESET_ALL}")
                elif key in ["-", "_"]:  # - key (with or without shift)
                    player.volume_down()
                    print(f"\r{Fore.GREEN}Volume: {player.get_volume_percentage()}%{Style.RESET_ALL}")
                else:
                    # Unknown key - just refresh status
                    pass
    
                # Brief pause to show command feedback
                time.sleep(0.1)
            
            # Update status line periodically (every 0.5 seconds)
            current_time = time.time()
            if current_time - last_status_update > 0.5:
                print_status_line(player.get_status_line())
                last_status_update = current_time
            
            time.sleep(0.05)  # Small delay to prevent excessive CPU usage
            
    except KeyboardInterrupt:
        stop_event.set()
    finally:
        keyboard.cleanup()
        # Print final newline for clean exit
        print()


def print_controls_help():
    """Print available keyboard controls with better formatting"""
    print(f"\n{Fore.CYAN}Keyboard Controls:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}S{Style.RESET_ALL} - Start/Stop (resets to beginning)")
    print(f"  {Fore.GREEN}P{Style.RESET_ALL} - Play/Pause (from current position)")
    print(f"  {Fore.GREEN}L{Style.RESET_ALL} - Toggle Loop")
    print(f"  {Fore.GREEN}+{Style.RESET_ALL} - Volume Up")
    print(f"  {Fore.GREEN}-{Style.RESET_ALL} - Volume Down")
    print(f"  {Fore.RED}Q{Style.RESET_ALL} - Quit")
    print()
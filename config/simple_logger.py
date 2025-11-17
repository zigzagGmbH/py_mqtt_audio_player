"""
Simple logging module that mirrors console output to a file.
Creates one log file named: {client_id}_{timestamp}.log
"""

# import os
# import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
import re

class ConsoleFileLogger:
    """
    Simple logger that captures console output to a file.
    File naming: {client_id}_{timestamp}.log
    """
    
    def __init__(self):
        self.log_file = None
        self.log_dir = None
        self.client_id = None
        self.max_size_mb = 5
        self.current_size = 0
        self._lock = threading.Lock()
        self.is_active = False
        
    def setup(self, client_id: str, log_dir: str = "logs", max_size_mb: int = 5):
        """
        Setup the logger
        Args:
            client_id: MQTT client ID (used in filename)
            log_dir: Directory for log files
            max_size_mb: Max file size before rotation
        """
        self.client_id = client_id
        self.log_dir = Path(log_dir)
        self.max_size_mb = max_size_mb
        
        # Create log directory
        self.log_dir.mkdir(exist_ok=True)
        
        # Create initial log file
        self._create_new_log_file()
        self.is_active = True
        
        # Log the startup
        self._write_to_file(f"[{self._timestamp()}] Logger started for client: {client_id}")
        
    def _timestamp(self):
        """Get current timestamp string"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _create_new_log_file(self):
        """Create a new log file with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.client_id}_{timestamp}.log"
        self.log_file = self.log_dir / filename
        self.current_size = 0
        
        # Write header to new file
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Audio Player Log - {self.client_id} ===\n")
            f.write(f"Started: {self._timestamp()}\n")
            f.write("=" * 50 + "\n\n")
    
    def _check_rotation(self):
        """Check if file needs rotation and rotate if necessary"""
        if self.current_size > (self.max_size_mb * 1024 * 1024):
            old_file = self.log_file.name
            self._write_to_file(f"[{self._timestamp()}] Log rotation - file size exceeded {self.max_size_mb}MB")
            self._create_new_log_file()
            self._write_to_file(f"[{self._timestamp()}] Log rotated from: {old_file}")
    
    def _clean_ansi_codes(self, text: str) -> str:
        """Remove ANSI color codes from text"""
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _write_to_file(self, message: str):
        """Write message to log file (thread-safe)"""
        if not self.is_active or not self.log_file:
            return
            
        with self._lock:
            try:
                # Clean message of ANSI codes
                clean_message = self._clean_ansi_codes(message)
                
                # Add timestamp if not already present
                if not clean_message.startswith('['):
                    clean_message = f"[{self._timestamp()}] {clean_message}"
                
                # Write to file
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(clean_message + '\n')
                    f.flush()  # Ensure immediate write
                
                # Update size tracking
                self.current_size += len(clean_message.encode('utf-8')) + 1
                
                # Check for rotation
                self._check_rotation()
                
            except Exception as e:
                # Don't let logging errors crash the app
                pass
    
    def log(self, message: str):
        """Log a message (public interface)"""
        self._write_to_file(message)
    
    def log_print(self, message: str):
        """Log a message that was printed to console"""
        # Extract the actual message content for cleaner logs
        clean_message = self._clean_ansi_codes(message)
        self._write_to_file(clean_message)
    
    def cleanup(self):
        """Cleanup and close logger"""
        if self.is_active:
            self._write_to_file(f"[{self._timestamp()}] Logger shutdown")
            self.is_active = False
    
    def get_current_log_file(self) -> Optional[str]:
        """Get path to current log file"""
        return str(self.log_file) if self.log_file else None
    
    def get_log_files(self) -> list:
        """Get list of all log files for this client"""
        if not self.log_dir.exists():
            return []
        
        pattern = f"{self.client_id}_*.log"
        log_files = []
        
        for log_file in self.log_dir.glob(pattern):
            stats = log_file.stat()
            log_files.append({
                'name': log_file.name,
                'path': str(log_file),
                'size_mb': stats.st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return sorted(log_files, key=lambda x: x['modified'], reverse=True)

# Global logger instance
_logger = ConsoleFileLogger()

def setup_logging(client_id: str, log_dir: str = "logs", max_size_mb: int = 5):
    """Setup the global logger"""
    _logger.setup(client_id, log_dir, max_size_mb)

def log(message: str):
    """Log a message"""
    _logger.log(message)

def log_print(message: str):
    """Log a message that was printed to console"""
    _logger.log_print(message)

def cleanup_logging():
    """Cleanup logging"""
    _logger.cleanup()

def get_current_log_file() -> Optional[str]:
    """Get current log file path"""
    return _logger.get_current_log_file()

def get_log_files() -> list:
    """Get all log files"""
    return _logger.get_log_files()

# Enhanced print function that also logs
original_print = print

def print_and_log(*args, **kwargs):
    """Enhanced print that also logs to file"""
    # Call original print
    original_print(*args, **kwargs)
    
    # Convert args to string like print does
    message = ' '.join(str(arg) for arg in args)
    
    # Log to file
    log_print(message)

def enable_auto_logging():
    """Replace built-in print with logging version"""
    import builtins
    builtins.print = print_and_log

def disable_auto_logging():
    """Restore original print function"""
    import builtins
    builtins.print = original_print
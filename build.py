#!/usr/bin/env python3
"""
Simple cross-platform build script for MQTT Audio Player
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


class BuildManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        
    def clean_build(self):
        """Clean previous build artifacts"""
        print("🧹 Cleaning previous builds...")
        for dir_path in [self.dist_dir, self.build_dir]:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                
    def build_executable(self):
        """Build the executable using PyInstaller"""
        print("🔨 Building executable...")
        
        # Simple PyInstaller command - let it auto-detect everything
        cmd = [
            "uv", "run", "pyinstaller", 
            "--onefile",
            "--name", "audio-player",
            "--add-data", "config.yaml:.",
            "--add-data", "audio:audio",
            "main.py"
        ]
        
        subprocess.run(cmd, check=True)
        
    def copy_to_root(self):
        """Copy the built executable to project root for easy access"""
        exe_name = "audio-player"
        if platform.system() == "Windows":
            exe_name += ".exe"
            
        src = self.dist_dir / exe_name
        dst = self.project_root / exe_name
        
        if src.exists():
            shutil.copy2(src, dst)
            # Make executable on Unix
            if platform.system() != "Windows":
                os.chmod(dst, 0o755)
            print(f"✅ Executable ready: ./{exe_name}")
            return True
        else:
            print("❌ Build failed - no executable found")
            return False
        
    def build(self):
        """Main build process"""
        try:
            self.clean_build()
            self.build_executable()
            return self.copy_to_root()
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


if __name__ == "__main__":
    builder = BuildManager()
    success = builder.build()
    
    if success:
        print("🎉 Build complete!")
        exe_name = "audio-player.exe" if platform.system() == "Windows" else "audio-player"
        print(f"🚀 Run with: ./{exe_name}")
    
    sys.exit(0 if success else 1)
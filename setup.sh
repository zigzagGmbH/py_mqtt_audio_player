#!/bin/bash
# Simple setup script for MQTT Audio Player

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

command_exists() { command -v "$1" &> /dev/null; }

echo -e "\n${BLUE}===== MQTT Audio Player Setup =====${NC}\n"

# Install uv if needed
if ! command_exists uv; then
    print_info "Installing uv..."
    if [[ "$OSTYPE" == "darwin"* ]] && command_exists brew; then
        brew install uv
    else
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source ~/.bashrc &> /dev/null || source ~/.bash_profile &> /dev/null || source ~/.profile &> /dev/null
    fi
    
    if ! command_exists uv; then
        print_error "uv installation failed"
        exit 1
    fi
    print_info "uv installed successfully!"
fi

# Clean and install
print_info "Installing dependencies..."
rm -rf build dist *.egg-info *.spec audio-player audio-player.exe 2>/dev/null
uv sync

# Menu
echo -e "\n${YELLOW}What would you like to do?${NC}"
echo "1) Run the audio player (development mode)"
echo "2) Build standalone executable"
echo "3) Just setup (done)"

read -p "Choose [1-3]: " choice

case $choice in
    1)
        print_info "Starting audio player..."
        uv run main.py
        ;;
    2)
        print_info "Building executable..."
        uv add --group dev pyinstaller
        if uv run build.py; then
            print_info "Build complete! Ready to run..."
            rm -rf build dist *.egg-info *.spec 2>/dev/null
            echo -e "\n${BLUE}Your executable is ready:${NC} ./audio-player"
            echo -e "${YELLOW}Run it with:${NC} ./audio-player"
        else
            print_error "Build failed"
            exit 1
        fi
        ;;
    3)
        print_info "Setup complete!"
        ;;
esac

echo -e "\n${GREEN}Usage:${NC}"
echo -e "  ${BLUE}Development:${NC} uv run main.py"
echo -e "  ${BLUE}Build binary:${NC} uv run build.py"
echo -e "  ${BLUE}Run binary:${NC} ./audio-player"
echo -e "\n${GREEN}Config:${NC} Edit config.yaml | Place .wav files in audio/"
echo -e "${GREEN}Done! 🎵${NC}\n"
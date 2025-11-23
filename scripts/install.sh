#!/bin/bash
# Installation script for commit-reflect
# Usage: curl -sSL https://raw.githubusercontent.com/yourusername/commit-reflect/main/scripts/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing commit-reflect...${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

echo "Detected OS: $OS"
echo "Detected Architecture: $ARCH"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}pip3 not found, attempting to install...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-pip
    elif command -v brew &> /dev/null; then
        brew install python3
    else
        echo -e "${RED}Error: Could not install pip3. Please install it manually.${NC}"
        exit 1
    fi
fi

# Install commit-reflect via pip
echo -e "${GREEN}Installing commit-reflect package...${NC}"
pip3 install --user commit-reflect

# Add to PATH if not already there
INSTALL_DIR="$HOME/.local/bin"
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}Adding $INSTALL_DIR to PATH...${NC}"

    # Detect shell
    if [ -n "$BASH_VERSION" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_RC="$HOME/.zshrc"
    else
        SHELL_RC="$HOME/.profile"
    fi

    echo "export PATH=\"\$PATH:$INSTALL_DIR\"" >> "$SHELL_RC"
    echo -e "${GREEN}Added to $SHELL_RC${NC}"
    echo -e "${YELLOW}Please run: source $SHELL_RC${NC}"
fi

# Verify installation
if command -v commit-reflect &> /dev/null; then
    VERSION=$(commit-reflect --version)
    echo -e "${GREEN}✓ commit-reflect installed successfully!${NC}"
    echo -e "${GREEN}  Version: $VERSION${NC}"
else
    echo -e "${RED}Error: Installation completed but commit-reflect command not found${NC}"
    echo -e "${YELLOW}Try running: source $SHELL_RC${NC}"
    exit 1
fi

# Optional: Initialize in current directory
echo ""
read -p "Initialize commit-reflect in current directory? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    commit-reflect init
    echo -e "${GREEN}✓ Initialized commit-reflect in current directory${NC}"
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Quick start:"
echo "  1. Make a commit: git commit -m 'your message'"
echo "  2. Reflect: commit-reflect"
echo "  3. View reflections: commit-reflect list"
echo ""
echo "For more information:"
echo "  commit-reflect --help"
echo "  https://github.com/yourusername/commit-reflect"

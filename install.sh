#!/bin/bash
set -e

# Change to the directory of the script
CDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$CDIR"

echo "Checking for Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

echo "Creating temporary virtual environment in .install..."
# Remove existing .install if it exists to start fresh
rm -rf .install
python3 -m venv .install
source .install/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
# Install the current package (installs runtime deps like svgwrite, cairosvg, etc.)
# and PyInstaller explicitly.
pip install . pyinstaller

echo "Building svgtree binary..."
# Run PyInstaller from the venv
pyinstaller --clean --onefile --add-data "default-theme.toml:." src/svg_tree/main.py --name svgtree

echo "Installing binary to ~/.local/bin..."
mkdir -p ~/.local/bin
cp dist/svgtree ~/.local/bin/

echo "Installing configuration to XDG config dir..."
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/svgtree"
ASSETS_DIR="$CONFIG_DIR/assets"
mkdir -p "$ASSETS_DIR"
cp default-theme.toml "$CONFIG_DIR/"
echo "Assets will be stored in: $ASSETS_DIR"

echo "Cleaning up build artifacts..."
deactivate
rm -rf .install build svgtree.spec

echo "------------------------------------------------"
echo "Installation complete!"
echo "Binary location: ~/.local/bin/svgtree"
echo "Config location: $CONFIG_DIR/default-theme.toml"
echo "Make sure ~/.local/bin is in your PATH."
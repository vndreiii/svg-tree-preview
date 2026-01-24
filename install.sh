#!/bin/bash
set -e

# Resolve script directory to ensure relative paths work
CDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$CDIR"

echo "Detected System: $(uname -s)"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

echo "Creating temporary build environment (.install_venv)..."
rm -rf .install_venv
python3 -m venv .install_venv
source .install_venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip

# Attempt install. If cairosvg fails due to missing system headers, warn the user.
if ! pip install . pyinstaller; then
    echo "------------------------------------------------"
    echo "Error: Failed to install Python dependencies."
    echo "If the error is related to 'cairosvg' or 'cffi', you may need system libraries:"
    echo "  - Debian/Ubuntu: sudo apt install libcairo2-dev"
    echo "  - Fedora: sudo dnf install cairo-devel"
    echo "  - Arch: sudo pacman -S cairo"
    echo "  - macOS: brew install cairo"
    echo "------------------------------------------------"
    deactivate
    exit 1
fi

echo "Building standalone binary with PyInstaller..."
# --clean: Clean PyInstaller cache
# --noconfirm: Don't ask to overwrite
# --onefile: Single executable
# --add-data: Bundle the default config
pyinstaller --clean --noconfirm --onefile --add-data "default-theme.toml:." src/svg_tree/main.py --name svgtree

echo "Installing binary..."
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
cp dist/svgtree "$BIN_DIR/"

echo "Installing configuration..."
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/svgtree"
ASSETS_DIR="$CONFIG_DIR/assets"
mkdir -p "$ASSETS_DIR"

# Only overwrite default theme if it doesn't exist? 
# Or always update default-theme.toml but leave user themes alone?
# Let's overwrite default-theme.toml to ensure updates are applied. 
# Users should create custom themes separate from default.
cp default-theme.toml "$CONFIG_DIR/"

echo "Cleaning up build artifacts..."
deactivate
rm -rf .install_venv build dist svgtree.spec

echo "------------------------------------------------"
echo "✓ Installation complete!"
echo "Binary installed to: $BIN_DIR/svgtree"
echo "Configuration at:    $CONFIG_DIR/default-theme.toml"
echo "Assets cached at:    $ASSETS_DIR"
echo ""
echo "Ensure $BIN_DIR is in your PATH."

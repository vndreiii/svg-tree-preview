#!/bin/bash
set -e

# Resolve script directory to ensure relative paths work
CDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$CDIR"

echo "Detected System: $(uname -s)"

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install it from https://docs.astral.sh/uv/"
    exit 1
fi

echo "Building wheel with uv..."
uv build --wheel --clear

echo "Packaging with Shiv..."
# Shiv creates a zipapp that includes all dependencies.
# IMPORTANT: We use the system's python3 explicitly for the build and as the target
# interpreter. This ensures that C extensions (like Pillow/PIL) are compiled for 
# the same Python version that will run the binary on this system (e.g., Python 3.14).
# Using uv's default managed Python (e.g., 3.12) would result in 'ImportError' 
# when the system's python3 tries to load those incompatible shared objects.
mkdir -p dist
SYSTEM_PYTHON=$(which python3)
uv run --python "$SYSTEM_PYTHON" shiv --compressed -e svg_tree.main:main -o dist/svgtree .

echo "Installing binary..."
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
cp dist/svgtree "$BIN_DIR/"
chmod +x "$BIN_DIR/svgtree"

echo "Installing configuration..."
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/svgtree"
ASSETS_DIR="$CONFIG_DIR/assets"
mkdir -p "$ASSETS_DIR"
cp default-theme.toml "$CONFIG_DIR/"

echo "Cleaning up build artifacts..."
# We keep dist/ for reference but could clean if desired
# rm -rf build/

echo "------------------------------------------------"
echo "✓ Installation complete (via Shiv)!"
echo "Binary installed to: $BIN_DIR/svgtree"
echo "Configuration at:    $CONFIG_DIR/default-theme.toml"
echo "Assets cached at:    $ASSETS_DIR"
echo ""
echo "Ensure $BIN_DIR is in your PATH."
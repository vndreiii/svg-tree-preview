#!/bin/bash
set -e

BIN_PATH="$HOME/.local/bin/svgtree"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/svgtree"

read -p "Are you sure you want to uninstall svgtree? This will remove the binary and all configuration/assets. [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Aborted."
    exit 1
fi

echo "Uninstalling svgtree..."

if [ -f "$BIN_PATH" ]; then
    rm "$BIN_PATH"
    echo "✓ Removed binary: $BIN_PATH"
else
    echo "• Binary not found at $BIN_PATH"
fi

if [ -d "$CONFIG_DIR" ]; then
    rm -rf "$CONFIG_DIR"
    echo "✓ Removed configuration and assets: $CONFIG_DIR"
else
    echo "• Configuration directory not found at $CONFIG_DIR"
fi

echo "Uninstallation complete."

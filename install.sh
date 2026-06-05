#!/usr/bin/env bash
# Ketoko POS Print Service — installer for Linux & macOS

set -e

PLATFORM="$(uname -s)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Ketoko POS Print Service Installer ==="
echo "Platform: $PLATFORM"

# Install Python deps
if command -v pip3 &>/dev/null; then
    pip3 install --user -r "$SCRIPT_DIR/requirements.txt"
elif command -v pip &>/dev/null; then
    pip install --user -r "$SCRIPT_DIR/requirements.txt"
else
    echo "ERROR: pip tidak ditemukan. Install Python 3 terlebih dahulu."
    exit 1
fi

if [ "$PLATFORM" = "Linux" ]; then
    # Systemd user service
    SERVICE_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SERVICE_DIR"

    sed "s|%h|$HOME|g" "$SCRIPT_DIR/ketoko-print.service" \
        > "$SERVICE_DIR/ketoko-print.service"

    systemctl --user daemon-reload
    systemctl --user enable --now ketoko-print.service
    echo "✓ Service aktif (systemd user)"

elif [ "$PLATFORM" = "Darwin" ]; then
    # LaunchAgent
    PLIST_DIR="$HOME/Library/LaunchAgents"
    PLIST_DST="$PLIST_DIR/id.ketoko.print.plist"
    mkdir -p "$PLIST_DIR"

    sed "s|SCRIPT_DIR|$SCRIPT_DIR|g" \
        "$SCRIPT_DIR/id.ketoko.print.plist" > "$PLIST_DST"

    launchctl unload "$PLIST_DST" 2>/dev/null || true
    launchctl load -w "$PLIST_DST"
    echo "✓ Service aktif (LaunchAgent)"
fi

echo ""
echo "Test: curl -s -X POST http://localhost:5488/readconf"
echo "Config: $SCRIPT_DIR/config.json"

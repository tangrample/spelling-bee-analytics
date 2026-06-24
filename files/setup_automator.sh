#!/bin/bash
#
# 🐝 Spelling Bee iCloud Watcher Setup
# Uses launchd WatchPaths to auto-process data whenever
# you save a file to iCloud Drive/Spelling Bee/ from your iPhone.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICLOUD_BEE_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Spelling Bee"
PLIST_LABEL="com.manasa.spellingbee.icloud"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

echo ""
echo "🐝 Spelling Bee iCloud Watcher Setup"
echo "======================================"
echo ""

# ── 1. Create iCloud Drive folder ─────────────────────────────────────────────
echo "Step 1/3 — Creating iCloud Drive folder..."
mkdir -p "$ICLOUD_BEE_DIR"
mkdir -p "$ICLOUD_BEE_DIR/processed"
echo "         ✓ ~/iCloud Drive/Spelling Bee/ is ready"
echo ""

# ── 2. Make scripts executable ────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/auto_process_icloud.sh"

# ── 3. Install launchd WatchPaths job ─────────────────────────────────────────
echo "Step 2/3 — Installing iCloud folder watcher..."

# Unload existing job if present
launchctl unload "$PLIST_PATH" 2>/dev/null || true

cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${SCRIPT_DIR}/auto_process_icloud.sh</string>
    </array>

    <!-- Fire whenever anything changes in the iCloud Spelling Bee folder -->
    <key>WatchPaths</key>
    <array>
        <string>${ICLOUD_BEE_DIR}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>

    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/bee_sync.log</string>

    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/bee_sync_error.log</string>
</dict>
</plist>
PLIST

launchctl load "$PLIST_PATH"

if launchctl list | grep -q "$PLIST_LABEL"; then
    echo "         ✓ Folder watcher installed and running"
else
    echo "         ⚠️  launchctl load may have failed — check that the path is correct"
fi
echo ""

# ── 4. Remove old schedule if present ─────────────────────────────────────────
echo "Step 3/3 — Cleaning up old scheduled sync..."
OLD_PLIST="$HOME/Library/LaunchAgents/com.manasa.spellingbee.sync.plist"
if [ -f "$OLD_PLIST" ]; then
    launchctl unload "$OLD_PLIST" 2>/dev/null || true
    rm -f "$OLD_PLIST"
    echo "         ✓ Removed old nightly schedule"
else
    echo "         ℹ️  No old schedule found"
fi
echo ""

# ── Summary ────────────────────────────────────────────────────────────────────
echo "======================================"
echo "✅ Setup complete!"
echo ""
echo "   Your daily workflow:"
echo "   1. Finish playing Spelling Bee on your iPhone"
echo "   2. Tap the 🐝 Save Bee Data bookmark in Safari"
echo "   3. Save the file to: Files → iCloud Drive → Spelling Bee"
echo "   4. Done — Mac processes it automatically within seconds ✨"
echo ""
echo "   iPhone bookmarklet setup: open iphone_bookmarklet_setup.html in Safari"
echo "   (AirDrop it to yourself or open it from Files on your iPhone)"
echo ""

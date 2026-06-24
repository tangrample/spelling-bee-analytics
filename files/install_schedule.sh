#!/bin/bash
#
# 🐝 Install daily 1pm ET bee sync schedule
# Run once: bash ~/Desktop/AI\ projects/spelling-bee-analytics/files/install_schedule.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_LABEL="com.manasa.spellingbee.daily"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

echo ""
echo "🐝 Installing daily 1pm sync..."

# Unload existing if present
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
        <string>${SCRIPT_DIR}/bee_sync.sh</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>13</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>

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
    echo "✅ Done — bee will run automatically at 1pm ET every day the Mac is on"
    echo "   (If the Mac is asleep at 1pm, it runs next time it wakes)"
else
    echo "⚠️  Loaded but couldn't confirm — check ~/Library/LaunchAgents/$PLIST_LABEL.plist"
fi
echo ""

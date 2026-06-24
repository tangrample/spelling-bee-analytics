#!/bin/bash
#
# 🐝 Spelling Bee iCloud Auto-Processor
# Triggered by launchd WatchPaths whenever the iCloud Spelling Bee folder changes.
# Finds any unprocessed JSON files, runs them through the pipeline, then archives them.
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICLOUD_BEE_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Spelling Bee"
ARCHIVE_DIR="$ICLOUD_BEE_DIR/processed"
LOG="$SCRIPT_DIR/bee_sync.log"

cd "$SCRIPT_DIR"

echo "" >> "$LOG"
echo "$(date): 🐝 auto_process_icloud triggered" >> "$LOG"

# Give iCloud Drive a moment to finish downloading the file
sleep 3

# Make sure archive folder exists
mkdir -p "$ARCHIVE_DIR"

# Find unprocessed JSON files in the Spelling Bee iCloud folder
FOUND=0
for FILE in "$ICLOUD_BEE_DIR"/spelling_bee_*.json; do
    [ -f "$FILE" ] || continue   # skip if glob matched nothing
    FOUND=1
    BASENAME="$(basename "$FILE")"
    echo "$(date): Processing $BASENAME" >> "$LOG"

    # Copy to project dir as spelling_bee_raw.json
    cp "$FILE" "$SCRIPT_DIR/spelling_bee_raw.json"

    # Run smart update
    python3 "$SCRIPT_DIR/smart_update.py" --mode smart >> "$LOG" 2>&1
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "$(date): ✅ Done" >> "$LOG"
        # Archive the processed file so it won't be reprocessed
        mv "$FILE" "$ARCHIVE_DIR/$BASENAME"
    else
        echo "$(date): ❌ Failed (exit $EXIT_CODE)" >> "$LOG"
        osascript -e 'display notification "Something went wrong — check bee_sync.log" with title "⚠️ Spelling Bee Sync Failed" sound name "Basso"'
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "$(date): No new files to process" >> "$LOG"
fi

#!/bin/bash
#
# Auto-update Spelling Bee with notification
# Use this with Shortcuts or Automator
#

# Set working directory (using absolute path for Shortcuts compatibility)
cd /Users/manasa/Desktop/spelling-bee-analytics/files

# Run the update script and capture output
OUTPUT=$(./update_spelling_bee.sh 2>&1)
EXIT_CODE=$?

# Check if update was successful
if [ $EXIT_CODE -eq 0 ]; then
    # Success notification
    osascript -e 'display notification "Your analytics database has been updated!" with title "✅ Spelling Bee Updated" sound name "Glass"'
    echo "✅ Update successful"
else
    # Error notification
    osascript -e 'display notification "There was an error updating. Check the logs." with title "⚠️ Update Failed" sound name "Basso"'
    echo "❌ Update failed"
    echo "$OUTPUT"
fi

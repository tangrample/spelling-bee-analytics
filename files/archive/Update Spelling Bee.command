#!/bin/bash
# Double-click this file in Finder to update your Spelling Bee database.
# (First time only: right-click → Open to bypass Gatekeeper)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🐝 Spelling Bee Updater"
echo "========================"
echo ""

# Make sure the script is being run from the right place
if [ ! -f "fetch_archive.py" ]; then
    echo "❌ Can't find project files. Make sure this file is in your spelling-bee folder."
    read -p "Press Enter to close..."
    exit 1
fi

python3 update_spelling_bee.sh 2>/dev/null || bash update_spelling_bee.sh

echo ""
read -p "Done! Press Enter to close this window..."

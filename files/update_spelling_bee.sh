#!/bin/bash
#
# NYT Spelling Bee Daily Data Update Script
# Run this manually whenever you want to capture your game data
# Recommend running daily to build history before yesterday's puzzle disappears
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "NYT SPELLING BEE DATA UPDATE"
echo "=========================================="
echo ""

# Step 1: Check for data in Downloads first (always prefer fresh data)
DOWNLOADS="$HOME/Downloads/spelling_bee_raw.json"
if [ -f "$DOWNLOADS" ]; then
    echo "📥 Found spelling_bee_raw.json in Downloads, moving it here..."
    mv "$DOWNLOADS" "spelling_bee_raw.json"
    echo "✓ File moved successfully"
    echo ""
elif [ ! -f "spelling_bee_raw.json" ]; then
    # No file in Downloads and no local file
    echo "❌ spelling_bee_raw.json not found!"
    echo ""
    echo "Please extract data using the bookmarklet:"
    echo "1. Open ONE_CLICK_SETUP.html and drag bookmarklet to Safari bookmarks bar"
    echo "2. Go to https://www.nytimes.com/puzzles/spelling-bee"
    echo "3. Click the bookmarklet in your bookmarks bar"
    echo "4. Run this script again"
    echo ""
    exit 1
else
    echo "ℹ️  Using existing spelling_bee_raw.json (no new file in Downloads)"
    echo ""
fi

# Step 2: Parse the raw data
echo "📝 Parsing raw data..."
python3 parse_nyt_data.py
echo ""

# Step 3: Ensure database has correct schema
echo "🔧 Checking database schema..."
if [ -f "spelling_bee.db" ]; then
    # Check if database has the new schema (puzzle_date column)
    if ! python3 -c "import sqlite3; conn = sqlite3.connect('spelling_bee.db'); cursor = conn.cursor(); cursor.execute('PRAGMA table_info(games)'); cols = [col[1] for col in cursor.fetchall()]; exit(0 if 'puzzle_date' in cols else 1)" 2>/dev/null; then
        echo "⚠️  Old database schema detected. Backing up and recreating..."
        mv spelling_bee.db spelling_bee.db.backup
        python3 create_database.py
    else
        echo "✓ Database schema is current"
    fi
else
    echo "🔧 Creating new database..."
    python3 create_database.py
fi
echo ""

# Step 4: Update database
echo "💾 Updating database..."
python3 process_data.py
echo ""

# Step 4: Show summary
echo "=========================================="
echo "✅ UPDATE COMPLETE"
echo "=========================================="
echo ""
echo "Your Spelling Bee analytics database has been updated!"
echo ""
echo "To view your stats, you can query spelling_bee.db"
echo "Example: python3 analyze.py"
echo ""

# Step 5: Auto-fill any gaps using Safari session (fetch_archive.py)
echo "🔍 Checking for missing historical dates..."
if python3 fetch_archive.py --dry-run 2>/dev/null | grep -q "Missing dates"; then
    echo "📥 Fetching missing archive data automatically..."
    python3 fetch_archive.py
else
    echo "✓ No gaps found — database is fully up to date"
fi
echo ""

# Optional: Show latest data
if command -v sqlite3 &> /dev/null; then
    echo "Recent games:"
    sqlite3 spelling_bee.db "SELECT puzzle_date, rank_achieved, score, total_words_found FROM games ORDER BY puzzle_date DESC LIMIT 5"
else
    echo "Tip: Install sqlite3 to see quick stats"
fi

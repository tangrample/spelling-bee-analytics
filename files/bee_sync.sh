#!/bin/bash
#
# 🐝 Spelling Bee Smart Sync
#
# Usage:
#   bee              → auto-detect data from clipboard / Downloads / iCloud, then sync
#   bee --force      → save all puzzles with any progress
#   bee --status     → preview without making changes
#
# Data sources (checked in order):
#   1. Clipboard     — if it contains valid bee JSON (from Mac bookmarklet)
#   2. Downloads     — spelling_bee_*.json files (from old bookmarklet download)
#   3. iCloud        — ~/iCloud Drive/Downloads/Spelling Bee/*.json (from iPhone bookmarklet)
#   If none found, falls back to existing spelling_bee_raw.json
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOWNLOADS="$HOME/Downloads"
ICLOUD_BEE="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Spelling Bee"
RAW_FILE="$SCRIPT_DIR/spelling_bee_raw.json"
cd "$SCRIPT_DIR"

MODE="smart"
if [[ "$1" == "--force" ]]; then MODE="force"; fi
if [[ "$1" == "--status" ]]; then MODE="status"; fi

# ── Export analytics + push to GitHub Pages ───────────────────────────────────
export_and_push() {
    [[ "$MODE" == "status" ]] && return 0
    echo ""
    echo "📊 Exporting analytics..."
    python3 "$SCRIPT_DIR/export_analytics.py" || { echo "⚠️  Export failed — skipping push"; return 1; }
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"
    cd "$REPO_ROOT"
    if ! git rev-parse --git-dir &>/dev/null; then
        echo "⚠️  Not a git repo — skipping push (run setup first)"
        cd "$SCRIPT_DIR"; return 0
    fi
    git add docs/data.json 2>/dev/null
    if git diff --cached --quiet 2>/dev/null; then
        echo "📊 Dashboard unchanged"
    else
        git commit -m "Update analytics $(date +%Y-%m-%d)" --quiet \
            && git push origin main --quiet \
            && echo "🚀 Dashboard updated on GitHub Pages" \
            || echo "⚠️  Push failed (no internet?) — will retry next sync"
    fi
    cd "$SCRIPT_DIR"
}

echo ""
echo "🐝 Spelling Bee Smart Sync"
echo "=========================="
echo ""

# ── Helper: validate bee JSON (reads directly from clipboard via pbpaste) ─────
is_clipboard_valid_bee_json() {
    pbpaste | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    keys = list(d.keys())
    has_state = any('games-state' in k for k in keys)
    print('  [debug] clipboard keys: ' + str(keys[:3]), file=sys.stderr)
    print('  [debug] has games-state: ' + str(has_state), file=sys.stderr)
    sys.exit(0 if has_state else 1)
except Exception as e:
    print('  [debug] clipboard JSON parse failed: ' + str(e)[:80], file=sys.stderr)
    sys.exit(1)
"
}

# ── Helper: process one raw file then run sync ────────────────────────────────
process_file() {
    local src="$1"
    local label="$2"
    echo "📥 Found bee data in $label — using it"
    cp "$src" "$RAW_FILE"
}

archive_icloud() {
    local f="$1"
    mkdir -p "$ICLOUD_BEE/processed"
    mv "$f" "$ICLOUD_BEE/processed/"
}

# ── Source 1: Clipboard ───────────────────────────────────────────────────────
echo "  [debug] checking clipboard ($(pbpaste 2>/dev/null | wc -c | tr -d ' ') bytes)..."
if is_clipboard_valid_bee_json; then
    echo "📋 Clipboard contains valid bee data — using it"
    pbpaste > "$RAW_FILE"
    echo ""

# ── Source 2: Downloads ───────────────────────────────────────────────────────
elif LATEST_DL=$(ls -t "$DOWNLOADS"/spelling_bee_*.json 2>/dev/null | head -1) && [ -n "$LATEST_DL" ]; then
    process_file "$LATEST_DL" "Downloads"
    rm "$LATEST_DL"
    echo ""

# ── Source 3: iCloud ──────────────────────────────────────────────────────────
elif ls "$ICLOUD_BEE"/spelling_bee_*.json &>/dev/null 2>&1; then
    # Process each iCloud file in sequence (handles multiple saved days)
    FIRST=1
    for f in "$ICLOUD_BEE"/spelling_bee_*.json; do
        [ -f "$f" ] || continue
        if [ "$FIRST" = "1" ]; then
            process_file "$f" "iCloud ($(basename "$f"))"
            echo ""
            FIRST=0
        else
            echo "📥 Also found $(basename "$f") in iCloud — processing separately"
            cp "$f" "$RAW_FILE"
        fi
        archive_icloud "$f"
        python3 "$SCRIPT_DIR/smart_update.py" --mode "$MODE"
    done
    echo ""
    export_and_push
    exit 0

# ── Fallback: existing raw file ───────────────────────────────────────────────
elif [ -f "$RAW_FILE" ]; then
    echo "ℹ️  No new data found — using existing spelling_bee_raw.json"
    echo ""

else
    echo "❌ No bee data found anywhere."
    echo ""
    echo "   iPhone → tap 🐝 bookmarklet → save to iCloud Drive → Spelling Bee"
    echo "   Mac    → click 🐝 bookmarklet (copies to clipboard) → run 'bee'"
    echo ""
    exit 1
fi

# ── Run smart update ──────────────────────────────────────────────────────────
python3 "$SCRIPT_DIR/smart_update.py" --mode "$MODE"
SYNC_EXIT=$?
[[ $SYNC_EXIT -eq 0 ]] && export_and_push
exit $SYNC_EXIT

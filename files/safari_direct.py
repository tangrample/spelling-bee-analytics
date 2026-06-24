#!/usr/bin/env python3
"""
Reads NYT Spelling Bee game states directly from Safari's localStorage
database on disk — no bookmarklet, no browser interaction needed.

Usage: python3 ~/spelling_bee/safari_direct.py [--open-pages]
"""

import glob
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

PUZZLE_DATES_NEEDED = ['2026-03-24', '2026-03-25', '2026-03-26']

# ── Find Safari's localStorage SQLite file for nytimes.com ───────────────────

def find_nyt_localstorage():
    home = Path.home()
    search_roots = [
        home / 'Library/WebKit/com.apple.Safari/WebsiteData/Default',
        home / 'Library/Containers/com.apple.Safari/Data/Library/WebKit/WebsiteData/Default',
        home / 'Library/Safari/LocalStorage',
    ]
    candidates = []
    for root in search_roots:
        if root.exists():
            for f in root.rglob('*.sqlite'):
                if 'nytimes' in str(f).lower():
                    candidates.append(f)
            for f in root.rglob('*.localstorage'):
                if 'nytimes' in str(f).lower():
                    candidates.append(f)

    # Also try the ITP-partitioned WebKit storage (macOS Ventura+)
    itp_roots = list(home.glob('Library/WebKit/com.apple.Safari/WebsiteData/v2/*nytimes*'))
    for root in itp_roots:
        for f in root.rglob('*.sqlite'):
            candidates.append(f)

    return candidates


def read_localstorage_from_sqlite(db_path):
    """Try reading localStorage key-value pairs from a WebKit SQLite database."""
    try:
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # WebKit localStorage schema: ItemTable(key TEXT, value BLOB)
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]

        results = {}
        if 'ItemTable' in tables:
            cur.execute("SELECT key, value FROM ItemTable")
            for row in cur.fetchall():
                key = row['key']
                if any(x in key for x in ['spelling_bee', 'spelling-bee', 'sb-', 'games-state']):
                    raw = row['value']
                    if isinstance(raw, bytes):
                        try:
                            raw = raw.decode('utf-8')
                        except Exception:
                            raw = raw.decode('utf-16-le', errors='replace')
                    try:
                        results[key] = json.loads(raw)
                    except Exception:
                        results[key] = raw

        conn.close()
        return results
    except Exception as e:
        return {}


# ── Load puzzle metadata from existing raw file ───────────────────────────────

def load_puzzle_metadata():
    raw_file = SCRIPT_DIR / 'spelling_bee_raw.json'
    if not raw_file.exists():
        return {}

    with open(raw_file) as f:
        data = json.load(f)

    window_data = data.get('_window_gameData', {})
    past = window_data.get('pastPuzzles', {})

    id_to_meta = {}
    def index(p):
        if p and p.get('id'):
            id_to_meta[str(p['id'])] = p

    for dk in ['today', 'yesterday']:
        index(past.get(dk))
    for wk in ['thisWeek', 'lastWeek']:
        for p in (past.get(wk) or []):
            index(p)

    return id_to_meta


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    open_pages = '--open-pages' in sys.argv

    print("🔍 Searching for Safari's NYT localStorage database...")
    candidates = find_nyt_localstorage()

    if not candidates:
        print("❌ Could not find Safari localStorage for nytimes.com.")
        print("   Try: run this script with --open-pages to open puzzle pages first.")
        sys.exit(1)

    print(f"   Found {len(candidates)} candidate file(s):")
    for c in candidates:
        print(f"   • {c}")

    # If requested, open each puzzle page first to ensure states are loaded
    if open_pages:
        for date in PUZZLE_DATES_NEEDED:
            url = f'https://www.nytimes.com/puzzles/spelling-bee/{date}'
            print(f"\n🌐 Opening {url} in Safari...")
            subprocess.run(['open', '-a', 'Safari', url])
            time.sleep(12)

    # Read all candidates and merge
    all_states = {}
    for db_path in candidates:
        data = read_localstorage_from_sqlite(db_path)
        for key, val in data.items():
            if 'games-state-spelling_bee' in key and not key.endswith('/ANON'):
                print(f"\n✅ Found authenticated game state key: {key}")
                states = val.get('states', [])
                for s in states:
                    pid = str(s.get('puzzleId', ''))
                    words = s.get('data', {}).get('answers', [])
                    all_states[pid] = s
                    print(f"   puzzleId={pid}, words={len(words)}")

    if not all_states:
        print("\n❌ No authenticated spelling bee game states found in Safari's database.")
        print("   Safari may not have written the states to disk yet.")
        print("   Try: Run with --open-pages to open past puzzle pages first,")
        print("   then run again (without --open-pages) after Safari has loaded them.")
        sys.exit(1)

    # Load metadata
    id_to_meta = load_puzzle_metadata()

    # Build merged data structure like spelling_bee_raw.json
    raw_file = SCRIPT_DIR / 'spelling_bee_raw.json'
    with open(raw_file) as f:
        existing = json.load(f)

    # Inject found states
    auth_key = None
    for k in existing:
        if 'games-state-spelling_bee' in k and not k.endswith('/ANON'):
            auth_key = k
            break

    if auth_key:
        current_states = existing[auth_key].get('states', [])
        current_pids = {str(s.get('puzzleId')) for s in current_states}
        added = 0
        for pid, state in all_states.items():
            if pid not in current_pids:
                meta = id_to_meta.get(pid, {})
                date = meta.get('printDate', '?')
                words = state.get('data', {}).get('answers', [])
                if words:
                    current_states.append(state)
                    current_pids.add(pid)
                    added += 1
                    print(f"✅ Added puzzleId={pid} ({date}) with {len(words)} words")
                else:
                    print(f"⚠️  puzzleId={pid} ({date}) has 0 words — skipping")
        existing[auth_key]['states'] = current_states
        print(f"\n📦 Injected {added} new game state(s) into spelling_bee_raw.json")
    else:
        print("❌ No authenticated key found in existing raw file.")
        sys.exit(1)

    # Save merged file
    with open(raw_file, 'w') as f:
        json.dump(existing, f)

    print("💾 Saved updated spelling_bee_raw.json")
    print("\nNow running bee sync...")

    result = subprocess.run(
        ['python3', str(SCRIPT_DIR / 'smart_update.py'), '--mode', 'force'],
        capture_output=False
    )
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()

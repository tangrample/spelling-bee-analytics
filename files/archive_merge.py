#!/usr/bin/env python3
"""
Archive Merge — combines bee_archive_YYYY-MM-DD.json snippets with your
existing spelling_bee_raw.json, then runs the normal parse + database update.

Run this after visiting all missing archive puzzle pages and downloading
their snippets via archive_extract.js.
"""

import json
import subprocess
import sys
from pathlib import Path

RAW_FILE     = Path('spelling_bee_raw.json')
ARCHIVE_GLOB = 'bee_archive_*.json'

def main():
    print('=' * 60)
    print('SPELLING BEE ARCHIVE MERGE')
    print('=' * 60)

    # ── 1. Find archive snippet files ───────────────────────────────────────
    snippets = sorted(Path('.').glob(ARCHIVE_GLOB))
    if not snippets:
        # Also check Downloads folder
        downloads = Path.home() / 'Downloads'
        snippets  = sorted(downloads.glob(ARCHIVE_GLOB))
        if snippets:
            print(f'📥 Found {len(snippets)} snippet(s) in Downloads — moving here...')
            moved = []
            for s in snippets:
                dest = Path(s.name)
                s.rename(dest)
                moved.append(dest)
            snippets = moved
        else:
            print('❌ No bee_archive_*.json files found.')
            print('   Run archive_extract.js on each missing archive puzzle first.')
            sys.exit(1)

    print(f'\n📂 Found {len(snippets)} archive snippet(s):')
    for s in snippets:
        print(f'   {s.name}')

    # ── 2. Load existing raw data ────────────────────────────────────────────
    if not RAW_FILE.exists():
        print(f'\n❌ {RAW_FILE} not found — run the main extraction first.')
        sys.exit(1)

    with open(RAW_FILE) as f:
        raw = json.load(f)

    # ── 3. Get or build the _window_gameData structure ───────────────────────
    game_data = raw.get('_window_gameData', {})

    # Collect existing puzzle metadata keyed by puzzle_id and date
    existing_by_id   = {}
    existing_by_date = {}

    def _index(puzzle):
        if not puzzle or not isinstance(puzzle, dict):
            return
        pid  = str(puzzle.get('id', puzzle.get('puzzleId', '')))
        date = puzzle.get('printDate', puzzle.get('date', ''))
        if pid:
            existing_by_id[pid] = puzzle
        if date:
            existing_by_date[date] = puzzle

    # Index existing pastPuzzles
    past = game_data.get('pastPuzzles', {})
    for key in ('today', 'yesterday'):
        _index(past.get(key) or game_data.get(key))
    for week in ('thisWeek', 'lastWeek'):
        for p in (past.get(week) or []):
            _index(p)

    # ── 4. Merge archive snippets ────────────────────────────────────────────
    added   = []
    skipped = []

    for snippet_path in snippets:
        with open(snippet_path) as f:
            s = json.load(f)

        date = s.get('date', '')
        pid  = s.get('puzzle_id', '')

        if date in existing_by_date or (pid and pid in existing_by_id):
            skipped.append(date or pid)
            continue

        # Convert snippet shape → NYT puzzle shape expected by parse_nyt_data.py
        puzzle_entry = {
            'id':           int(pid) if pid else None,
            'printDate':    date,
            'centerLetter': s.get('center_letter', ''),
            'outerLetters': s.get('outer_letters', []),
            'answers':      s.get('all_words', []),
            'pangrams':     s.get('pangrams', []),
            '_from_archive': True,
        }

        # Add to thisWeek list (parse_nyt_data.py iterates all of them)
        if 'pastPuzzles' not in game_data:
            game_data['pastPuzzles'] = {'thisWeek': [], 'lastWeek': []}
        if 'thisWeek' not in game_data['pastPuzzles']:
            game_data['pastPuzzles']['thisWeek'] = []

        game_data['pastPuzzles']['thisWeek'].append(puzzle_entry)
        existing_by_date[date] = puzzle_entry
        added.append(date)

    print(f'\n✅ Added:   {len(added)} new puzzle(s): {", ".join(sorted(added)) or "none"}')
    if skipped:
        print(f'⊘  Skipped: {len(skipped)} already present: {", ".join(sorted(skipped))}')

    if not added:
        print('\nNothing new to add — database is already up to date for these dates.')
        sys.exit(0)

    # ── 5. Write updated raw file ────────────────────────────────────────────
    raw['_window_gameData'] = game_data

    backup = RAW_FILE.with_suffix('.json.bak')
    RAW_FILE.rename(backup)
    print(f'\n💾 Backed up original to {backup.name}')

    with open(RAW_FILE, 'w') as f:
        json.dump(raw, f, indent=2)
    print(f'💾 Updated {RAW_FILE.name} with {len(added)} new puzzle(s)')

    # ── 6. Run the normal pipeline ───────────────────────────────────────────
    print('\n' + '─' * 60)
    print('Running parse_nyt_data.py...')
    print('─' * 60)
    subprocess.run([sys.executable, 'parse_nyt_data.py'], check=True)

    print('\n' + '─' * 60)
    print('Running process_data.py...')
    print('─' * 60)
    subprocess.run([sys.executable, 'process_data.py'], check=True)

    # ── 7. Clean up snippet files ─────────────────────────────────────────────
    print('\n🧹 Cleaning up snippet files...')
    for s in snippets:
        if Path(s).exists():
            Path(s).unlink()
            print(f'   Deleted {s.name}')

    print('\n' + '=' * 60)
    print('✅ ARCHIVE MERGE COMPLETE')
    print('=' * 60)


if __name__ == '__main__':
    main()

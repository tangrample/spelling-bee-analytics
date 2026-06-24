#!/usr/bin/env python3
"""
fetch_archive.py — One-command archive backfill for NYT Spelling Bee.

Reads your Safari login session, figures out which puzzle dates are missing
from your database, fetches them from NYT, and updates everything.

Usage:
    python3 fetch_archive.py
    python3 fetch_archive.py --dates 2026-03-31 2026-04-10   # specific range
    python3 fetch_archive.py --dry-run                        # just show what's missing
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

# ── Dependency bootstrap ────────────────────────────────────────────────────

def pip_install(*pkgs):
    # Try plain install first; if that fails (e.g. externally managed env),
    # fall back to --user. --break-system-packages only exists in pip 22.3+.
    for extra in [[], ['--user']]:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-q', *extra, *pkgs],
        )
        if result.returncode == 0:
            return
    print(f'❌ Could not auto-install {pkgs}. Run manually: pip install {" ".join(pkgs)}')
    sys.exit(1)

try:
    import requests
except ImportError:
    print('Installing requests...'); pip_install('requests')
    import requests

try:
    import browser_cookie3
except ImportError:
    print('Installing browser-cookie3...'); pip_install('browser-cookie3')
    import browser_cookie3

# ── Constants ───────────────────────────────────────────────────────────────

DB_FILE      = Path('spelling_bee.db')
RAW_FILE     = Path('spelling_bee_raw.json')
NYT_BASE     = 'https://www.nytimes.com'
NYT_DOMAIN   = '.nytimes.com'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                  'Version/17.0 Safari/605.1.15',
    'Accept': 'text/html,application/xhtml+xml,application/json,*/*',
    'Referer': 'https://www.nytimes.com/puzzles/spelling-bee',
}

# ── Database helpers ─────────────────────────────────────────────────────────

def get_db_dates():
    """Return set of puzzle_date strings already in the database."""
    if not DB_FILE.exists():
        return set()
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()
    cur.execute('SELECT puzzle_date FROM games')
    dates = {row[0] for row in cur.fetchall()}
    conn.close()
    return dates

def get_game_state_dates():
    """
    Return set of dates implied by game states in spelling_bee_raw.json.
    Falls back to an empty set if the file isn't available yet.
    """
    if not RAW_FILE.exists():
        return set()
    with open(RAW_FILE) as f:
        raw = json.load(f)
    game_data = raw.get('_window_gameData', {})
    dates = set()
    past  = game_data.get('pastPuzzles', {})
    for key in ('today', 'yesterday'):
        p = past.get(key) or game_data.get(key)
        if p and 'printDate' in p:
            dates.add(p['printDate'])
    for week in ('thisWeek', 'lastWeek'):
        for p in (past.get(week) or []):
            if 'printDate' in p:
                dates.add(p['printDate'])
    return dates

# ── Safari cookie loader ─────────────────────────────────────────────────────

def load_safari_cookies():
    """Load NYT cookies from Safari. Returns a requests.cookies.RequestsCookieJar."""
    print('🍪 Reading NYT cookies from Safari...')
    try:
        jar = browser_cookie3.safari(domain_name=NYT_DOMAIN)
        nyt_cookies = {c.name: c.value for c in jar if NYT_DOMAIN in c.domain or 'nytimes' in c.domain}
        if not nyt_cookies:
            raise ValueError('No NYT cookies found')
        print(f'   ✓ Found {len(nyt_cookies)} NYT cookie(s)')
        # Check for session cookie
        if 'NYT-S' in nyt_cookies:
            print('   ✓ NYT-S session cookie present (logged in)')
        else:
            print('   ⚠  NYT-S not found — you may not be logged in to Safari')
        return jar
    except Exception as e:
        print(f'\n❌ Could not read Safari cookies: {e}')
        print('\nFix: Make sure you are logged into NYT in Safari, then try again.')
        print('     You may also need to grant Terminal access to Safari data in:')
        print('     System Settings → Privacy & Security → Full Disk Access')
        sys.exit(1)

# ── Puzzle data extraction strategies ───────────────────────────────────────

def _is_puzzle_shape(obj):
    return (
        isinstance(obj, dict) and
        ('centerLetter' in obj or 'center_letter' in obj) and
        ('outerLetters' in obj or 'outer_letters' in obj) and
        ('answers' in obj or 'validLetters' in obj or 'validWords' in obj)
    )

def _deep_find_puzzle(obj, depth=0, seen=None):
    if seen is None:
        seen = set()
    if depth > 10 or not isinstance(obj, dict):
        return None
    obj_id = id(obj)
    if obj_id in seen:
        return None
    seen.add(obj_id)
    if _is_puzzle_shape(obj):
        return obj
    for v in obj.values():
        if isinstance(v, dict):
            r = _deep_find_puzzle(v, depth + 1, seen)
            if r:
                return r
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    r = _deep_find_puzzle(item, depth + 1, seen)
                    if r:
                        return r
    return None

def extract_puzzle_from_html(html, target_date):
    """Try multiple strategies to extract puzzle data from an HTML page."""

    # Strategy 1: Next.js __NEXT_DATA__ script tag
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if m:
        try:
            next_data = json.loads(m.group(1))
            puzzle = _deep_find_puzzle(next_data)
            if puzzle:
                return puzzle
        except Exception:
            pass

    # Strategy 2: window.__data or window.gameData inline assignment
    for pattern in [
        r'window\.gameData\s*=\s*(\{.*?\});?\s*(?:window|var|let|const|</script>)',
        r'window\.__data\s*=\s*(\{.*?\});?\s*(?:window|var|let|const|</script>)',
        r'"today"\s*:\s*(\{[^{}]*"centerLetter"[^{}]*\})',
    ]:
        for m in re.finditer(pattern, html, re.DOTALL):
            try:
                obj = json.loads(m.group(1))
                puzzle = _deep_find_puzzle(obj) or (obj if _is_puzzle_shape(obj) else None)
                if puzzle:
                    return puzzle
            except Exception:
                pass

    # Strategy 3: Find any JSON blob containing centerLetter + printDate
    for m in re.finditer(r'\{[^{}]{20,}"centerLetter"[^{}]+\}', html):
        try:
            obj = json.loads(m.group(0))
            if _is_puzzle_shape(obj):
                return obj
        except Exception:
            pass

    # Strategy 4: Broader search — find centerLetter and build object from context
    m = re.search(r'"centerLetter"\s*:\s*"([A-Z])"', html, re.IGNORECASE)
    if m:
        # Try to grab a large surrounding chunk and parse
        idx = html.index(m.group(0))
        chunk_start = max(0, html.rfind('{', 0, idx) - 0)
        for window in [2000, 5000, 10000]:
            chunk = html[max(0, idx - window): idx + window]
            # Find the first { before our match
            start = chunk.rfind('{')
            if start == -1:
                continue
            # Walk to find matching }
            depth = 0
            for i in range(start, len(chunk)):
                if chunk[i] == '{':
                    depth += 1
                elif chunk[i] == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(chunk[start:i+1])
                            if _is_puzzle_shape(obj):
                                return obj
                        except Exception:
                            pass
                        break

    return None

def normalize_puzzle(raw: dict, target_date: str) -> dict:
    """Normalize raw puzzle data to the shape parse_nyt_data.py expects."""
    return {
        'id':           raw.get('id') or raw.get('puzzleId'),
        'printDate':    raw.get('printDate') or raw.get('print_date') or target_date,
        'centerLetter': (raw.get('centerLetter') or raw.get('center_letter') or '').upper(),
        'outerLetters': [l.upper() for l in (raw.get('outerLetters') or raw.get('outer_letters') or [])],
        'answers':      raw.get('answers') or raw.get('validWords') or [],
        'pangrams':     raw.get('pangrams') or [],
        '_fetched':     True,
    }

# ── Fetch a single puzzle date ───────────────────────────────────────────────

def fetch_puzzle(target_date, session):
    """Try multiple URLs/strategies to fetch puzzle data for a given date."""

    urls_to_try = [
        # Direct JSON APIs (might exist)
        f'{NYT_BASE}/svc/spelling-bee/v1/{target_date}.json',
        f'{NYT_BASE}/svc/spelling-bee/v2/{target_date}.json',
        f'{NYT_BASE}/puzzles/spelling-bee/{target_date}',   # Archive page (HTML)
        f'{NYT_BASE}/puzzles/spelling-bee',                 # Main page
    ]

    for url in urls_to_try:
        try:
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue

            content_type = resp.headers.get('Content-Type', '')

            # Pure JSON response
            if 'json' in content_type:
                try:
                    data = resp.json()
                    puzzle = _deep_find_puzzle(data)
                    if puzzle:
                        norm = normalize_puzzle(puzzle, target_date)
                        if norm['printDate'] == target_date or not norm['printDate']:
                            norm['printDate'] = target_date
                            return norm
                except Exception:
                    pass

            # HTML response — parse for embedded data
            else:
                puzzle = extract_puzzle_from_html(resp.text, target_date)
                if puzzle:
                    norm = normalize_puzzle(puzzle, target_date)
                    # Verify it's actually the right date
                    if norm['printDate'] and norm['printDate'] != target_date:
                        continue  # wrong puzzle, try next URL
                    norm['printDate'] = target_date
                    return norm

        except requests.RequestException:
            continue

    return None

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Fetch missing Spelling Bee archive data')
    parser.add_argument('--dates', nargs=2, metavar=('START', 'END'),
                        help='Date range to fetch (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show missing dates without fetching')
    args = parser.parse_args()

    print('=' * 60)
    print('SPELLING BEE ARCHIVE FETCHER')
    print('=' * 60)

    # ── Determine missing dates ──────────────────────────────────────────────
    db_dates = get_db_dates()

    if args.dates:
        start = date.fromisoformat(args.dates[0])
        end   = date.fromisoformat(args.dates[1])
        candidate_range = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        missing = [str(d) for d in candidate_range if str(d) not in db_dates]
    else:
        # Auto-detect: find gaps between first DB date and today
        if not db_dates:
            print('❌ No data in database yet. Run the main extraction first.')
            sys.exit(1)
        first = date.fromisoformat(min(db_dates))
        today = date.today()
        candidate_range = [first + timedelta(days=i) for i in range((today - first).days + 1)]
        missing = [str(d) for d in candidate_range if str(d) not in db_dates]

    if not missing:
        print('\n✅ No missing dates — your database is fully up to date!')
        return

    print(f'\n📅 Missing dates ({len(missing)}):')
    for d in missing:
        print(f'   {d}')

    if args.dry_run:
        print('\n(dry-run — not fetching)')
        return

    # ── Load Safari cookies ──────────────────────────────────────────────────
    jar     = load_safari_cookies()
    session = requests.Session()
    session.cookies = jar

    # ── Fetch each missing date ──────────────────────────────────────────────
    print(f'\n🌐 Fetching {len(missing)} puzzle(s) from NYT...\n')
    fetched  = {}
    failed   = []

    for d in missing:
        print(f'   {d} ... ', end='', flush=True)
        puzzle = fetch_puzzle(d, session)
        if puzzle:
            fetched[d] = puzzle
            letters = puzzle.get('centerLetter', '?') + ''.join(puzzle.get('outerLetters', []))
            n_words = len(puzzle.get('answers', []))
            print(f'✓  ({letters}, {n_words} words)')
        else:
            failed.append(d)
            print('✗  (not found)')

    print(f'\n📊 Fetched: {len(fetched)}   Failed: {len(failed)}')
    if failed:
        print(f'   Could not retrieve: {", ".join(failed)}')
        print('   (These might be dates you didn\'t play, or require visiting the archive page manually)')

    if not fetched:
        print('\nNothing to update.')
        return

    # ── Merge into spelling_bee_raw.json ─────────────────────────────────────
    print(f'\n💾 Merging into {RAW_FILE}...')
    with open(RAW_FILE) as f:
        raw = json.load(f)

    game_data = raw.setdefault('_window_gameData', {})
    past      = game_data.setdefault('pastPuzzles', {})
    this_week = past.setdefault('thisWeek', [])

    existing_dates = {p.get('printDate') for p in this_week if 'printDate' in p}
    for d, puzzle in fetched.items():
        if d not in existing_dates:
            this_week.append(puzzle)

    backup = RAW_FILE.with_suffix('.json.bak')
    import shutil
    shutil.copy(RAW_FILE, backup)

    with open(RAW_FILE, 'w') as f:
        json.dump(raw, f, indent=2)
    print(f'   ✓ Updated (backup saved as {backup.name})')

    # ── Run parse + process pipeline ─────────────────────────────────────────
    print('\n' + '─' * 60)
    print('Running parse_nyt_data.py...')
    print('─' * 60)
    subprocess.run([sys.executable, 'parse_nyt_data.py'], check=True)

    print('\n' + '─' * 60)
    print('Running process_data.py...')
    print('─' * 60)
    subprocess.run([sys.executable, 'process_data.py'], check=True)

    print('\n' + '=' * 60)
    print('✅ DONE')
    print('=' * 60)
    if failed:
        print(f'\n⚠  {len(failed)} date(s) could not be auto-fetched: {", ".join(failed)}')
        print('   For those, use archive_extract.js manually (open each in Safari,')
        print('   paste the script in the Console, then run: python3 archive_merge.py)')


if __name__ == '__main__':
    main()

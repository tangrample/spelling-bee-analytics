#!/usr/bin/env python3
"""
🐝 Spelling Bee Orchestrator
Navigates Safari to each undownloaded puzzle URL, extracts game state,
and saves to the database — fully automatic, no bookmarklet needed.

Modes:
  --mode smart   Save if revealed or GN4L achieved; remind otherwise (default)
  --mode force   Save all puzzles with any progress, ignore threshold
  --mode status  Preview what would happen, no changes made
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from process_data import calculate_word_points, is_pangram, is_gn4l, load_into_database

DATABASE_FILE = str(SCRIPT_DIR / 'spelling_bee.db')
NYT_BEE_URL   = 'https://www.nytimes.com/puzzles/spelling-bee'
ET_TZ         = ZoneInfo('America/New_York')
PAGE_LOAD_WAIT = 5  # seconds to wait after navigating to each puzzle


# ── AppleScript helpers ────────────────────────────────────────────────────────

def run_applescript(script: str) -> subprocess.CompletedProcess:
    """Write script to a temp file and run it (avoids shell escaping issues)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False) as f:
        f.write(script)
        path = f.name
    try:
        return subprocess.run(
            ['osascript', path], capture_output=True, text=True, timeout=30
        )
    finally:
        os.unlink(path)


def run_js(js_code: str) -> str:
    """Run JavaScript in the current Safari tab and return the result."""
    script = f'''tell application "Safari"
    set jsResult to do JavaScript {json.dumps(js_code)} in current tab of window 1
    return jsResult
end tell'''
    r = run_applescript(script)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or 'AppleScript failed')
    return r.stdout.strip()


def navigate_to(url: str):
    """Navigate the existing Spelling Bee tab (or open one) to the given URL."""
    script = f'''tell application "Safari"
    set targetURL to {json.dumps(url)}
    set beeTab to missing value
    set beeWin to missing value
    repeat with w in windows
        repeat with t in tabs of w
            if URL of t contains "nytimes.com/puzzles/spelling-bee" then
                set beeTab to t
                set beeWin to w
                exit repeat
            end if
        end repeat
        if beeTab is not missing value then exit repeat
    end repeat
    if beeTab is missing value then
        if (count of windows) = 0 then make new document
        set beeTab to make new tab in window 1 with properties {{URL: targetURL}}
        set beeWin to window 1
    else
        set URL of beeTab to targetURL
    end if
    set current tab of beeWin to beeTab
end tell'''
    r = run_applescript(script)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or 'Navigation failed')


# ── JavaScript snippets ────────────────────────────────────────────────────────

# Extracts all puzzle metadata from window.gameData.pastPuzzles (14-day window)
JS_GET_PUZZLE_META = """
(function() {
    if (!window.gameData || !window.gameData.pastPuzzles) return JSON.stringify(null);
    var pp = window.gameData.pastPuzzles;
    var out = {};
    function add(p) {
        if (!p || !p.id || !p.printDate) return;
        out[String(p.id)] = {
            id:           p.id,
            date:         p.printDate,
            centerLetter: p.centerLetter,
            outerLetters: p.outerLetters || [],
            validLetters: p.validLetters || [],
            answers:      p.answers      || [],
            pangrams:     p.pangrams     || []
        };
    }
    add(pp.today); add(pp.yesterday);
    (pp.thisWeek || []).forEach(add);
    (pp.lastWeek || []).forEach(add);
    return JSON.stringify(out);
})()
"""


def js_get_state_for_date(target_date: str) -> str:
    """Returns JS that finds the game state for a specific date in localStorage."""
    return f"""
(function() {{
    var gsKey = null;
    for (var i = 0; i < localStorage.length; i++) {{
        if (localStorage.key(i).indexOf('games-state') !== -1) {{
            gsKey = localStorage.key(i); break;
        }}
    }}
    if (!gsKey) return JSON.stringify(null);
    var gs = JSON.parse(localStorage.getItem(gsKey));
    var states = gs.states || [];
    for (var j = 0; j < states.length; j++) {{
        if (states[j].printDate === {json.dumps(target_date)}) {{
            return JSON.stringify(states[j]);
        }}
    }}
    return JSON.stringify(null);
}})()
"""


# ── Scoring helpers ────────────────────────────────────────────────────────────

def score_for_words(words: list, all_letters: str) -> int:
    return sum(calculate_word_points(w, is_pangram(w, all_letters)) for w in words)


def rank_from_pct(pct: float) -> str:
    if pct >= 100: return 'Queen Bee'
    elif pct >= 70: return 'Genius'
    elif pct >= 50: return 'Amazing'
    elif pct >= 40: return 'Great'
    elif pct >= 25: return 'Nice'
    elif pct >= 15: return 'Solid'
    elif pct >= 8:  return 'Good'
    elif pct >= 5:  return 'Moving Up'
    elif pct >= 2:  return 'Good Start'
    else:           return 'Beginner'


def days_until_expiry(puzzle_date_str: str) -> int:
    today = datetime.now(ET_TZ).date()
    try:
        pdate = datetime.strptime(puzzle_date_str, '%Y-%m-%d').date()
    except ValueError:
        return -1
    return max(13 - (today - pdate).days, -1)


# ── Notifications & Reminders ─────────────────────────────────────────────────

def notify(title: str, body: str, sound: str = 'Glass'):
    esc = lambda s: s.replace('"', '\\"')
    subprocess.run(['osascript', '-e',
        f'display notification "{esc(body)}" with title "{esc(title)}" sound name "{sound}"'])


def create_reminder(date_str: str, rank: str, score: int, max_score: int,
                    days_left: int, gn4l: bool):
    pct = round(score / max_score * 100) if max_score else 0
    if days_left <= 2:
        title = f"⚠️ Expiring soon: {date_str} puzzle"
        time_note = f"Only {days_left} day(s) left to save"
    else:
        title = f"🐝 Spelling Bee: {date_str} puzzle"
        time_note = f"{days_left} day(s) until data expires"
    gn4l_note = " You've hit GN4L!" if gn4l else ""
    body = (f"You're at {rank} ({pct}%, {score}/{max_score} pts). "
            f"{time_note}.{gn4l_note} Keep playing, or run 'bee' on the Mac to save.")
    now_et = datetime.now(ET_TZ)
    due = now_et.replace(hour=21, minute=0, second=0, microsecond=0)
    if due <= now_et:
        due = now_et + timedelta(hours=1)
    as_date = due.strftime('%m/%d/%Y %I:%M:%S %p')
    esc = lambda s: s.replace('"', '\\"').replace("'", "\\'")
    script = f'''tell application "Reminders"
    try
        set myList to list "Spelling Bee"
    on error
        set myList to make new list with properties {{name:"Spelling Bee"}}
    end try
    make new reminder at end of myList with properties {{¬
        name:"{esc(title)}", body:"{esc(body)}", due date:date "{as_date}"}}
end tell'''
    r = run_applescript(script)
    if r.returncode == 0:
        print(f"  📱 iPhone reminder created")
    else:
        notify(title, body, sound='Ping')


# ── Database ──────────────────────────────────────────────────────────────────

def get_existing_dates() -> set:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT puzzle_date FROM games")
    dates = {row[0] for row in cursor.fetchall()}
    conn.close()
    return dates


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smart', 'force', 'status'], default='smart')
    args = parser.parse_args()
    mode = args.mode

    if mode == 'status':  print("📋 STATUS MODE — no changes will be made\n")
    elif mode == 'force': print("💪 FORCE MODE — saving all puzzles with any progress\n")

    if not Path(DATABASE_FILE).exists():
        print("❌ Database not found. Run create_database.py first.")
        sys.exit(1)

    existing_dates = get_existing_dates()

    # ── Step 1: Load main page and get 14-day puzzle metadata ─────────────────
    print("🌐 Loading NYT Spelling Bee to get puzzle list...")
    try:
        navigate_to(NYT_BEE_URL)
        time.sleep(PAGE_LOAD_WAIT)
        meta_raw = run_js(JS_GET_PUZZLE_META)
        all_puzzles = json.loads(meta_raw) if meta_raw and meta_raw != 'null' else {}
    except RuntimeError as e:
        print(f"❌ Could not load NYT page: {e}")
        print("   Check: Safari → Develop → Allow JavaScript from Apple Events")
        notify("⚠️ Spelling Bee Sync Failed", str(e), sound='Basso')
        sys.exit(1)

    if not all_puzzles:
        print("❌ No puzzle data found. Make sure you are logged into NYT in Safari.")
        sys.exit(1)

    puzzles_by_date = {v['date']: v for v in all_puzzles.values()}
    missing = sorted(d for d in puzzles_by_date if d not in existing_dates)
    already_saved = sorted(d for d in puzzles_by_date if d in existing_dates)

    print(f"✓ {len(all_puzzles)} puzzles in window | "
          f"{len(already_saved)} already saved | "
          f"{len(missing)} to check\n")

    if not missing:
        print("✅ Everything is up to date — nothing to do!")
        notify("🐝 Spelling Bee", "Already up to date", sound='Purr')
        return

    # ── Step 2: For each missing date, navigate and extract ───────────────────
    saved, prompted, no_play, errors = [], [], [], []

    for date in missing:
        meta = puzzles_by_date[date]
        valid_letters = ''.join(meta.get('validLetters', []))  # all 7 letters
        all_words     = meta.get('answers', [])
        max_score     = score_for_words(all_words, valid_letters)

        print(f"📅 {date}", end='', flush=True)

        if mode == 'status':
            print(f"  →  would navigate to check game state")
            continue

        # Navigate to this puzzle's URL and extract state
        try:
            navigate_to(f"{NYT_BEE_URL}/{date}")
            time.sleep(PAGE_LOAD_WAIT)
            state_raw = run_js(js_get_state_for_date(date))
            state = json.loads(state_raw) if state_raw and state_raw != 'null' else None
        except Exception as e:
            print(f"  →  ⚠️  error: {e}")
            errors.append(date)
            continue

        if not state:
            print(f"  →  not played yet, skipping")
            no_play.append(date)
            continue

        game_data   = state.get('data', {})
        words_found = game_data.get('answers', [])
        is_revealed = game_data.get('isRevealed', False)
        rank_raw    = game_data.get('rank', '')

        if not words_found:
            print(f"  →  no words found, skipping")
            no_play.append(date)
            continue

        score    = score_for_words(words_found, valid_letters)
        pct      = score / max_score * 100 if max_score else 0
        rank     = rank_raw or rank_from_pct(pct)
        gn4l     = is_gn4l(words_found, valid_letters, max_score)
        days_left = days_until_expiry(date)

        print(f"  →  {rank} ({pct:.0f}%, {score}/{max_score}) | "
              f"GN4L: {'✓' if gn4l else '✗'} | "
              f"Revealed: {'✓' if is_revealed else '✗'} | "
              f"{days_left}d left")

        # ── Decision ──────────────────────────────────────────────────────────
        if mode == 'force' or is_revealed or gn4l:
            reason = 'force' if mode == 'force' else ('revealed' if is_revealed else 'GN4L')
            print(f"     💾 Saving ({reason})...")
            game_record = {
                'date':              date,
                'letters':           ''.join(meta.get('outerLetters', [])),
                'center_letter':     meta.get('centerLetter', ''),
                'words_found':       words_found,
                'all_possible_words': all_words,
                'pangrams':          meta.get('pangrams', []),
                # Mark as revealed so full answer key is stored
                'is_revealed':       True,
                'rank':              rank,
                'status':            'COMPLETE',
            }
            load_into_database([game_record])
            saved.append(date)
        else:
            create_reminder(date, rank, score, max_score, days_left, gn4l)
            prompted.append(date)

    # Navigate back to main page when done
    if mode != 'status':
        navigate_to(NYT_BEE_URL)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*52}")
    print(f"{'📋 STATUS' if mode == 'status' else '✅ SYNC COMPLETE'}")
    if saved:        print(f"   Saved:          {', '.join(saved)}")
    if prompted:     print(f"   Reminded:       {', '.join(prompted)}")
    if no_play:      print(f"   Not played:     {', '.join(no_play)}")
    if errors:       print(f"   Errors:         {', '.join(errors)}")
    if already_saved:print(f"   Already in DB:  {len(already_saved)} puzzle(s)")
    print()

    if mode != 'status':
        parts = []
        if saved:    parts.append(f"Saved {', '.join(saved)}")
        if prompted: parts.append(f"Reminder sent for {', '.join(prompted)}")
        if errors:   parts.append(f"{len(errors)} error(s) — check terminal")
        notify(
            "✅ Spelling Bee Synced" if (saved or prompted) else "🐝 Spelling Bee",
            " | ".join(parts) if parts else "Nothing new to save",
            sound='Glass' if saved else 'Purr'
        )


if __name__ == '__main__':
    main()

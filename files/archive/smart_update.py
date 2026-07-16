#!/usr/bin/env python3
"""
🧠 Smart Spelling Bee Update
Intelligently decides whether to save, skip, or prompt for each puzzle
based on its revealed/GN4L status and how close it is to expiring.

Modes:
  --mode smart    Save if revealed or GN4L achieved; remind otherwise (default)
  --mode force    Save all puzzles that have any progress, ignore threshold
  --mode status   Print status only, make no changes and send no reminders
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Path setup ─────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from parse_nyt_data import parse_nyt_localStorage
from process_data import (
    calculate_word_points,
    is_pangram,
    is_gn4l,
    load_into_database,
)

DATABASE_FILE = str(SCRIPT_DIR / 'spelling_bee.db')
RAW_FILE      = str(SCRIPT_DIR / 'spelling_bee_raw.json')
ET_TZ         = ZoneInfo('America/New_York')

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_existing_dates() -> set:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT puzzle_date FROM games")
    dates = {row[0] for row in cursor.fetchall()}
    conn.close()
    return dates


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


def score_for_words(words: list, letters: str) -> int:
    total = 0
    for word in words:
        is_pan = is_pangram(word, letters)
        total += calculate_word_points(word, is_pan)
    return total


def days_until_expiry(puzzle_date_str: str) -> int:
    """
    Returns how many more days this puzzle is accessible on NYT.
    NYT keeps 2 weeks of past puzzles. Returns -1 if already gone.
    """
    now_et = datetime.now(ET_TZ)
    today_et = now_et.date()
    try:
        puzzle_date = datetime.strptime(puzzle_date_str, '%Y-%m-%d').date()
    except ValueError:
        return -1

    days_old = (today_et - puzzle_date).days
    # NYT window is 14 days (today = 0 days old, still accessible)
    days_remaining = 13 - days_old
    return max(days_remaining, -1)


# ── iCloud Reminder ────────────────────────────────────────────────────────────

def create_icloud_reminder(date_str: str, rank: str, score: int,
                            max_score: int, days_left: int, gn4l: bool):
    """
    Create an iCloud Reminder that syncs to iPhone automatically.
    Scheduled for 9 PM ET today (or in 1 hour if it's already past 9 PM).
    """
    pct = round(score / max_score * 100) if max_score else 0

    if days_left <= 2:
        title = f"⚠️ Expiring soon: {date_str} puzzle"
        time_note = f"Only {days_left} day(s) left to save this puzzle"
    else:
        title = f"🐝 Spelling Bee: {date_str} puzzle"
        time_note = f"{days_left} day(s) until data expires"

    gn4l_note = " You've hit GN4L — run 'bee' to save!" if gn4l else ""
    body = (
        f"You're at {rank} ({pct}%, {score}/{max_score} pts). "
        f"{time_note}.{gn4l_note} "
        f"Keep playing on your phone, or run 'bee' on your Mac to save progress."
    )

    # Reminder time: 9 PM ET, or +1 hr if past 9 PM
    now_et = datetime.now(ET_TZ)
    due = now_et.replace(hour=21, minute=0, second=0, microsecond=0)
    if due <= now_et:
        due = now_et + timedelta(hours=1)
    as_date = due.strftime('%m/%d/%Y %I:%M:%S %p')

    esc = lambda s: s.replace('"', '\\"').replace("'", "\\'")

    script = f'''
tell application "Reminders"
    try
        set myList to list "Spelling Bee"
    on error
        set myList to make new list with properties {{name:"Spelling Bee"}}
    end try
    make new reminder at end of myList with properties {{¬
        name:"{esc(title)}", ¬
        body:"{esc(body)}", ¬
        due date:date "{as_date}"}}
end tell
'''
    result = subprocess.run(['osascript', '-e', script],
                            capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  📱 iPhone reminder created: {title}")
    else:
        print(f"  ⚠️  Reminders failed ({result.stderr.strip()}), falling back to Mac notification")
        notif = f'display notification "{esc(body)}" with title "{esc(title)}" sound name "Ping"'
        subprocess.run(['osascript', '-e', notif])


# ── macOS notification ─────────────────────────────────────────────────────────

def notify(title: str, body: str, sound: str = "Glass"):
    esc = lambda s: s.replace('"', '\\"')
    script = f'display notification "{esc(body)}" with title "{esc(title)}" sound name "{sound}"'
    subprocess.run(['osascript', '-e', script])


# ── Main logic ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['smart', 'force', 'status'],
                        default='smart')
    args = parser.parse_args()
    mode = args.mode

    if mode == 'status':
        print("📋 STATUS MODE — no changes will be made\n")
    elif mode == 'force':
        print("💪 FORCE MODE — saving all puzzles with any progress\n")

    # Validate prerequisites
    if not Path(RAW_FILE).exists():
        print("❌ spelling_bee_raw.json not found. Run bee_sync.sh first.")
        sys.exit(1)
    if not Path(DATABASE_FILE).exists():
        print("❌ Database not found. Run create_database.py first.")
        sys.exit(1)

    # Parse localStorage export
    games = parse_nyt_localStorage(RAW_FILE)
    if not games:
        print("❌ No Spelling Bee game data found in the extracted file.")
        print("   Make sure you are logged into NYT in Safari.")
        sys.exit(1)

    existing_dates = get_existing_dates()

    saved, skipped, prompted, no_progress = [], [], [], []
    games_to_save = []

    for game in games:
        date        = game.get('date', 'unknown')
        words_found = game.get('words_found', [])
        all_words   = game.get('all_possible_words', [])
        letters     = (game.get('letters') or '') + (game.get('center_letter') or '')
        is_revealed = game.get('is_revealed', False)

        print(f"📅 {date}", end='')

        # ── Already saved? ──
        if date in existing_dates:
            print(f"  →  already in database ✓")
            skipped.append(date)
            continue

        # ── No words found yet? ──
        if not words_found:
            print(f"  →  no words found, skipping")
            no_progress.append(date)
            continue

        # ── Calculate scores ──
        score     = score_for_words(words_found, letters)
        max_score = score_for_words(all_words, letters)
        pct       = score / max_score * 100 if max_score else 0
        rank      = rank_from_pct(pct)
        gn4l      = is_gn4l(words_found, letters, max_score)
        days_left = days_until_expiry(date)

        status_line = (
            f"  →  {rank} ({pct:.0f}%, {score}/{max_score}) | "
            f"GN4L: {'✓' if gn4l else '✗'} | "
            f"Revealed: {'✓' if is_revealed else '✗'} | "
            f"Expires in: {'TONIGHT' if days_left == 0 else f'{days_left}d'}"
        )
        print(status_line)

        # ── Decision ──
        should_save = False
        save_reason = ''

        if mode == 'force' and words_found:
            should_save = True
            save_reason = 'force mode'
        elif mode == 'status':
            if is_revealed or gn4l:
                print(f"     → Would save ({('revealed' if is_revealed else 'GN4L')})")
            else:
                print(f"     → Would remind (not yet at threshold)")
            continue
        elif is_revealed:
            should_save = True
            save_reason = 'puzzle revealed'
        elif gn4l:
            should_save = True
            save_reason = 'GN4L achieved'
            # Treat as revealed so the full answer key gets stored
            game = dict(game)
            game['is_revealed'] = True

        if should_save:
            print(f"     💾 Saving ({save_reason})...")
            games_to_save.append(game)
            saved.append(date)
        else:
            # Prompt user via iCloud Reminder
            if mode != 'status':
                create_icloud_reminder(date, rank, score, max_score, days_left, gn4l)
            prompted.append(date)

    # ── Write to database ──────────────────────────────────────────────────────
    if games_to_save:
        print(f"\n💾 Writing {len(games_to_save)} game(s) to database...")
        load_into_database(games_to_save)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*52}")
    print(f"{'📋 STATUS' if mode == 'status' else '✅ SYNC COMPLETE'}")
    if saved:
        print(f"   Saved:          {', '.join(saved)}")
    if skipped:
        print(f"   Already in DB:  {', '.join(skipped)}")
    if prompted:
        print(f"   Reminded:       {', '.join(prompted)}")
    if no_progress:
        print(f"   No progress:    {', '.join(no_progress)}")
    print()

    # ── Mac notification ───────────────────────────────────────────────────────
    if mode != 'status':
        parts = []
        if saved:      parts.append(f"Saved {', '.join(saved)}")
        if prompted:   parts.append(f"Reminder sent for {', '.join(prompted)}")
        if skipped:    parts.append(f"{len(skipped)} already up to date")

        if parts:
            notify("✅ Spelling Bee Synced", " | ".join(parts))
        else:
            notify("🐝 Spelling Bee", "Nothing new to sync", sound="Purr")


if __name__ == '__main__':
    main()

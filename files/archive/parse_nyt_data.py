#!/usr/bin/env python3
"""
Parse NYT Spelling Bee localStorage data
Handles the actual format from NYT's website
"""

import json
from pathlib import Path
from datetime import datetime

def parse_nyt_localStorage(localStorage_file='spelling_bee_raw.json'):
    """
    Parse the actual NYT localStorage format.
    
    The data structure is:
    {
      "games-state-spelling_bee/USER_ID": {
        "states": [
          {
            "puzzleId": "12345",
            "data": {
              "answers": ["word1", "word2", ...],
              "status": "IN_PROGRESS" or "COMPLETE",
              ...
            }
          }
        ]
      },
      "_window_gameData": {
        "today": {
          "printDate": "2026-02-08",
          "displayDate": "February 8, 2026",
          ...
        },
        "yesterday": {...}
      }
    }
    """
    
    with open(localStorage_file, 'r') as f:
        data = json.load(f)
    
    games = []
    
    # Find the games-state key — prefer an authenticated (non-ANON) key
    # because the ANON key only contains empty/guest game states.
    games_state_key = None
    anon_key = None
    for key in data.keys():
        if 'games-state-spelling_bee' in key:
            if key.endswith('/ANON'):
                anon_key = key       # save as fallback
            else:
                games_state_key = key  # prefer this
                break
    if not games_state_key:
        games_state_key = anon_key   # fall back to ANON if nothing else found
    
    if not games_state_key:
        print("❌ Could not find Spelling Bee game state in localStorage")
        return []
    
    game_states = data[games_state_key].get('states', [])

    # Also get the window game data for puzzle info
    window_data = data.get('_window_gameData', {})

    # Build puzzle metadata index from ALL available puzzles (up to 2 weeks).
    # pastPuzzles contains: today, yesterday, thisWeek (list), lastWeek (list).
    # Fall back to the top-level today/yesterday keys for older extractions.
    puzzles_info = {}

    def _index_puzzle(day_data):
        if not day_data or 'printDate' not in day_data:
            return
        puzzle_id = str(day_data.get('id', ''))
        if not puzzle_id:
            return
        puzzles_info[puzzle_id] = {
            'date': day_data['printDate'],
            'letters': ''.join(day_data.get('outerLetters', [])),
            'center_letter': day_data.get('centerLetter', ''),
            'all_words': day_data.get('answers', []),
            'pangrams': day_data.get('pangrams', []),
        }

    past = window_data.get('pastPuzzles', {})
    if past:
        # Preferred: richer pastPuzzles structure (today, yesterday, thisWeek, lastWeek)
        for day_key in ['today', 'yesterday']:
            _index_puzzle(past.get(day_key))
        for week_key in ['thisWeek', 'lastWeek']:
            for p in (past.get(week_key) or []):
                _index_puzzle(p)
    else:
        # Fallback: legacy top-level today/yesterday keys
        for day_key in ['today', 'yesterday']:
            _index_puzzle(window_data.get(day_key))

    print(f"\n📦 Found {len(game_states)} game state(s) in localStorage")
    print(f"📋 Found puzzle info for {len(puzzles_info)} puzzle(s) "
          f"({min(puzzles_info.values(), key=lambda x: x['date'])['date'] if puzzles_info else '—'}"
          f" → {max(puzzles_info.values(), key=lambda x: x['date'])['date'] if puzzles_info else '—'})\n")
    
    # Process each game state
    for state in game_states:
        puzzle_id = str(state.get('puzzleId', ''))
        game_data = state.get('data', {})

        # Get the words the player found
        words_found = game_data.get('answers', [])

        # Get raw data from game state
        is_revealed = game_data.get('isRevealed', False)
        rank = game_data.get('rank', '')

        # Skip if no words found (unsolved puzzle)
        if not words_found:
            print(f"  ⊘ Skipping puzzle {puzzle_id} - no words found (unsolved)")
            continue

        # Try to get puzzle info
        puzzle_info = puzzles_info.get(puzzle_id, {})

        # Skip puzzles with no metadata in the 2-week window
        if not puzzle_info:
            print(f"  ⊘ Skipping puzzle {puzzle_id} - no puzzle metadata found (outside 2-week window)")
            continue
        
        game_record = {
            'date': puzzle_info.get('date', f"puzzle-{puzzle_id}"),
            'puzzle_id': puzzle_id,
            'letters': puzzle_info.get('letters', ''),
            'center_letter': puzzle_info.get('center_letter', ''),
            'words_found': words_found,
            'all_possible_words': puzzle_info.get('all_words', []),
            'pangrams': puzzle_info.get('pangrams', []),
            'is_revealed': is_revealed,
            'rank': rank,
            'status': game_data.get('status', 'UNKNOWN')
        }
        
        games.append(game_record)
        print(f"  ✓ Parsed {game_record['date']}: {len(words_found)} words found")
    
    return games


def save_parsed_data(games, output_file='spelling_bee_parsed.json'):
    """Save the parsed data to a file."""
    
    with open(output_file, 'w') as f:
        json.dump(games, f, indent=2)
    
    print(f"\n✅ Saved {len(games)} games to {output_file}")
    print("\nNext step: Run process_data.py to load into database")


def main():
    print("=" * 70)
    print("NYT SPELLING BEE DATA PARSER")
    print("=" * 70)
    print("\nParsing spelling_bee_raw.json...\n")
    
    if not Path('spelling_bee_raw.json').exists():
        print("❌ spelling_bee_raw.json not found!")
        print("\nPlease extract your data using browser_extract.js first.")
        return
    
    games = parse_nyt_localStorage()
    
    if games:
        save_parsed_data(games)
    else:
        print("\n❌ No games found in localStorage")
        print("\nThis might mean:")
        print("  1. You haven't played any games yet")
        print("  2. The localStorage export is incomplete")
        print("  3. NYT changed their data structure")


if __name__ == '__main__':
    main()

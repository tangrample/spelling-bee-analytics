#!/usr/bin/env python3
"""
Process and load Spelling Bee data into database
Handles data cleaning, validation, and derived calculations
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DATABASE_FILE = 'spelling_bee.db'

def calculate_word_points(word: str, is_pangram: bool = False) -> int:
    """
    Calculate points for a word according to Spelling Bee rules.
    
    Rules:
    - 4-letter words: 1 point
    - 5+ letter words: 1 point per letter
    - Pangrams: +7 bonus points
    """
    if len(word) == 4:
        points = 1
    else:
        points = len(word)
    
    if is_pangram:
        points += 7
    
    return points


def is_pangram(word: str, all_letters: str) -> bool:
    """Check if word uses all 7 letters."""
    word_letters = set(word.lower())
    puzzle_letters = set(all_letters.lower())
    return puzzle_letters.issubset(word_letters)


def is_gn4l(words_found: List[str], all_letters: str, max_score: int) -> bool:
    """
    Check if player achieved GN4L (Genius No 4-Letter words).
    This means reaching Genius level (70% of max) using ONLY 5+ letter words.

    Returns True if points from 5+ letter words alone >= 70% of max score.
    """
    if max_score == 0:
        return False

    # Calculate score from 5+ letter words only
    points_from_5plus = 0
    for word in words_found:
        if len(word) >= 5:
            is_pan = is_pangram(word, all_letters)
            points_from_5plus += calculate_word_points(word, is_pan)

    # Check if 5+ letter words alone reach genius threshold (70%)
    genius_threshold = max_score * 0.70
    return points_from_5plus >= genius_threshold


def process_game_data(raw_data: Dict) -> Tuple[Dict, List[Dict], List[Dict]]:
    """
    Process raw game data into structured format.
    
    Returns:
        Tuple of (game_record, words_found, all_possible_words)
    """
    
    # Handle if raw_data is a string (parse it)
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse game data as JSON: {raw_data[:100]}")
    
    if not isinstance(raw_data, dict):
        raise ValueError(f"Game data is not a dictionary: {type(raw_data)}")
    
    # Extract basic game info - try multiple possible key names
    date = raw_data.get('date') or raw_data.get('printDate') or raw_data.get('gameDate') or ''
    letters = raw_data.get('letters') or raw_data.get('validLetters') or raw_data.get('outerLetters', '') + raw_data.get('centerLetter', '')
    center_letter = raw_data.get('center_letter') or raw_data.get('centerLetter') or raw_data.get('center', '')
    
    # Get words - try multiple formats
    words_found = raw_data.get('words_found') or raw_data.get('answers') or raw_data.get('words') or []
    all_possible = raw_data.get('all_possible_words') or raw_data.get('solutions') or []
    
    # If words are stored as a string, parse them
    if isinstance(words_found, str):
        try:
            words_found = json.loads(words_found)
        except:
            words_found = [w.strip() for w in words_found.split(',') if w.strip()]
    
    if isinstance(all_possible, str):
        try:
            all_possible = json.loads(all_possible)
        except:
            all_possible = [w.strip() for w in all_possible.split(',') if w.strip()]
    
    # Calculate scores and stats
    score = 0
    words_found_records = []
    
    for word in words_found:
        is_pan = is_pangram(word, letters)
        points = calculate_word_points(word, is_pan)
        score += points
        
        words_found_records.append({
            'word': word.lower(),
            'points': points,
            'is_pangram': is_pan,
            'length': len(word)
        })
    
    # Process all possible words if available
    all_possible_records = []
    max_score = 0
    
    for word in all_possible:
        is_pan = is_pangram(word, letters)
        points = calculate_word_points(word, is_pan)
        max_score += points
        
        all_possible_records.append({
            'word': word.lower(),
            'points': points,
            'is_pangram': is_pan,
            'length': len(word)
        })
    
    # Use raw rank from NYT if available, otherwise calculate as fallback
    rank = raw_data.get('rank', '')
    percentage = (score / max_score * 100) if max_score > 0 else 0

    # Calculate rank as fallback if not provided
    if not rank:
        if percentage == 100:
            rank = 'Queen Bee'
        elif percentage >= 70:
            rank = 'Genius'
        elif percentage >= 50:
            rank = 'Amazing'
        elif percentage >= 40:
            rank = 'Great'
        elif percentage >= 25:
            rank = 'Nice'
        elif percentage >= 15:
            rank = 'Solid'
        elif percentage >= 8:
            rank = 'Good'
        elif percentage >= 5:
            rank = 'Moving Up'
        elif percentage >= 2:
            rank = 'Good Start'
        else:
            rank = 'Beginner'

    # Determine achievements
    is_genius = percentage >= 70
    is_queen_bee = len(words_found) == len(all_possible) if all_possible else False
    is_gn4l_achieved = is_gn4l(words_found, letters, max_score)

    # Check if puzzle is revealed (from raw data or fallback to checking if we have answers)
    is_revealed = raw_data.get('is_revealed', bool(all_possible and len(all_possible) > 0))

    # Get current time in Eastern Time
    et_tz = ZoneInfo('America/New_York')
    current_time_et = datetime.now(et_tz).strftime('%Y-%m-%d %H:%M:%S')

    # Create game record
    game_record = {
        'puzzle_date': date,
        'puzzle_letters': letters.upper(),
        'center_letter': center_letter.upper(),
        'score': score,
        'max_possible_score': max_score if max_score > 0 else None,
        'rank_achieved': rank,
        'is_genius': is_genius,
        'is_queen_bee': is_queen_bee,
        'is_gn4l': is_gn4l_achieved,
        'is_revealed': is_revealed,
        'total_words_found': len(words_found),
        'total_possible_words': len(all_possible) if all_possible else None,
        'created_at_et': current_time_et,
        'updated_at_et': current_time_et
    }
    
    return game_record, words_found_records, all_possible_records


def load_into_database(games_data: List[Dict]):
    """Load processed data into SQLite database."""

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

    loaded_count = 0
    skipped_count = 0
    
    for raw_game in games_data:
        try:
            # Process the game data
            game, words_found, all_possible = process_game_data(raw_game)
            
            # Skip if this is a puzzle we haven't solved yet
            if not words_found:
                print(f"  ⊘ Skipping {game['puzzle_date']} - no words found (unsolved puzzle)")
                skipped_count += 1
                continue
            
            # Insert game record
            cursor.execute("""
                INSERT OR REPLACE INTO games (
                    puzzle_date, puzzle_letters, center_letter, score, max_possible_score,
                    rank_achieved, is_genius, is_queen_bee, is_gn4l, is_revealed,
                    total_words_found, total_possible_words, created_at_et, updated_at_et
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game['puzzle_date'], game['puzzle_letters'], game['center_letter'],
                game['score'], game['max_possible_score'], game['rank_achieved'],
                game['is_genius'], game['is_queen_bee'], game['is_gn4l'], game['is_revealed'],
                game['total_words_found'], game['total_possible_words'],
                game['created_at_et'], game['updated_at_et']
            ))
            
            game_id = cursor.lastrowid
            
            # Insert words found
            for word_rec in words_found:
                cursor.execute("""
                    INSERT OR REPLACE INTO words_found (
                        game_id, word, points, is_pangram, length
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    game_id, word_rec['word'], word_rec['points'],
                    word_rec['is_pangram'], word_rec['length']
                ))
            
            # Insert all possible words only if puzzle is revealed
            if game['is_revealed']:
                for word_rec in all_possible:
                    cursor.execute("""
                        INSERT OR REPLACE INTO puzzle_answers (
                            game_id, word, points, is_pangram, length
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        game_id, word_rec['word'], word_rec['points'],
                        word_rec['is_pangram'], word_rec['length']
                    ))
            
            loaded_count += 1
            print(f"  ✓ Loaded {game['puzzle_date']}: {game['total_words_found']} words, {game['score']} points")
            
        except Exception as e:
            print(f"  ✗ Error processing game: {e}")
            continue
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Loaded {loaded_count} games into database")
    print(f"  Skipped {skipped_count} unsolved puzzles")


def main():
    """Main entry point."""
    
    # Check if database exists
    if not Path(DATABASE_FILE).exists():
        print("Error: Database not found. Run create_database.py first.")
        return
    
    # Try to load parsed data first, then fall back to raw
    parsed_file = Path('spelling_bee_parsed.json')
    raw_file = Path('spelling_bee_raw.json')
    
    if parsed_file.exists():
        print("Using spelling_bee_parsed.json")
        with open(parsed_file, 'r') as f:
            games_data = json.load(f)
    elif raw_file.exists():
        print(f"Error: Found {raw_file} but not spelling_bee_parsed.json")
        print("\nPlease run parse_nyt_data.py first to parse the localStorage data:")
        print("  python3 parse_nyt_data.py")
        return
    else:
        print(f"Error: No data files found.")
        print("Run parse_nyt_data.py first.")
        return
    
    print(f"Processing {len(games_data)} games...\n")
    load_into_database(games_data)
    
    # Show summary
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM words_found")
    total_words = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE is_genius = 1")
    genius_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE is_queen_bee = 1")
    queen_bee_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM games WHERE is_gn4l = 1")
    gn4l_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("\nDatabase Summary:")
    print(f"  Total games: {total_games}")
    print(f"  Total words found: {total_words}")
    print(f"  Genius ranks: {genius_count}")
    print(f"  Queen Bee achievements: {queen_bee_count}")
    print(f"  GN4L achievements: {gn4l_count}")


if __name__ == '__main__':
    main()

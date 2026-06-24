#!/usr/bin/env python3
"""
NYT Spelling Bee Data Extractor
Extracts game history from browser localStorage and saves to structured format
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

def extract_from_localStorage_json(localStorage_file: Path) -> List[Dict]:
    """
    Extract Spelling Bee game data from a localStorage JSON export.
    
    The localStorage should contain a key like 'sb-today' or game-state data.
    You can export localStorage by:
    1. Opening Chrome DevTools (F12)
    2. Go to Application > Local Storage > https://www.nytimes.com
    3. Find keys starting with 'sb-' or containing spelling bee data
    4. Copy the JSON and save to a file
    
    Args:
        localStorage_file: Path to JSON file containing localStorage export
    
    Returns:
        List of game records
    """
    
    with open(localStorage_file, 'r') as f:
        data = json.load(f)
    
    games = []
    
    # The localStorage might have different structures, so we'll be flexible
    # Common keys: 'sb-today', game state data, etc.
    
    # If it's a direct export of the game state
    if isinstance(data, dict):
        # Look for common patterns in NYT Spelling Bee localStorage
        for key, value in data.items():
            if 'sb-' in key.lower() or 'spelling' in key.lower():
                try:
                    if isinstance(value, str):
                        value = json.loads(value)
                    
                    # Extract game data
                    if isinstance(value, dict):
                        game_data = extract_game_data(value)
                        if game_data:
                            games.append(game_data)
                except (json.JSONDecodeError, TypeError):
                    continue
    
    return games


def extract_game_data(game_state: Dict) -> Optional[Dict]:
    """
    Extract relevant game data from a single game state object.
    
    Args:
        game_state: Dictionary containing game state
    
    Returns:
        Structured game record or None
    """
    
    # Try to find the date
    date = None
    for date_key in ['date', 'printDate', 'gameDate', 'puzzleDate']:
        if date_key in game_state:
            date = game_state[date_key]
            break
    
    if not date:
        return None
    
    # Extract words found by the player
    words_found = []
    for key in ['answers', 'words', 'guesses', 'foundWords']:
        if key in game_state:
            words_found = game_state[key]
            if isinstance(words_found, str):
                words_found = json.loads(words_found)
            break
    
    # Extract all possible words (puzzle answers)
    all_words = []
    for key in ['answers', 'solutions', 'pangrams', 'validWords']:
        if key in game_state and key not in ['answers'] or 'all' in key.lower():
            all_words = game_state[key]
            if isinstance(all_words, str):
                all_words = json.loads(all_words)
            break
    
    # Extract the letters
    letters = game_state.get('letters', game_state.get('validLetters', ''))
    center_letter = game_state.get('centerLetter', game_state.get('center', ''))
    
    # Extract score/rank info
    score = game_state.get('score', game_state.get('points', 0))
    rank = game_state.get('rank', game_state.get('level', ''))
    
    return {
        'date': date,
        'words_found': words_found,
        'all_possible_words': all_words,
        'letters': letters,
        'center_letter': center_letter,
        'score': score,
        'rank': rank,
        'raw_data': game_state  # Keep raw data for reference
    }


def create_manual_entry() -> Dict:
    """
    Guide user through manual entry of game data.
    Useful if localStorage export doesn't work.
    
    Returns:
        Game record dictionary
    """
    print("\n=== Manual Game Entry ===\n")
    
    date = input("Enter game date (YYYY-MM-DD): ").strip()
    
    print("\nEnter the 7 letters from the puzzle (e.g., ABCDEFG):")
    letters = input("> ").strip().upper()
    
    print("\nEnter the center letter:")
    center_letter = input("> ").strip().upper()
    
    print("\nEnter words you found (comma-separated):")
    words_found = input("> ").strip().split(',')
    words_found = [w.strip().lower() for w in words_found if w.strip()]
    
    print("\nEnter the rank/level you reached (e.g., Genius, Amazing, etc.):")
    rank = input("> ").strip()
    
    # Calculate score from words
    score = calculate_score(words_found, letters)
    
    return {
        'date': date,
        'words_found': words_found,
        'all_possible_words': [],  # Will be populated later
        'letters': letters,
        'center_letter': center_letter,
        'score': score,
        'rank': rank,
        'manual_entry': True
    }


def calculate_score(words: List[str], all_letters: str) -> int:
    """
    Calculate Spelling Bee score for a list of words.
    
    Rules:
    - 4-letter words: 1 point
    - 5+ letter words: 1 point per letter
    - Pangrams (use all 7 letters): +7 bonus points
    
    Args:
        words: List of words
        all_letters: All 7 letters in the puzzle
    
    Returns:
        Total score
    """
    score = 0
    
    for word in words:
        if len(word) == 4:
            score += 1
        else:
            score += len(word)
        
        # Check if pangram
        if is_pangram(word, all_letters):
            score += 7
    
    return score


def is_pangram(word: str, all_letters: str) -> bool:
    """Check if a word uses all 7 letters at least once."""
    return all(letter.lower() in word.lower() for letter in all_letters)


def main():
    """Main entry point for the extraction script."""
    
    print("NYT Spelling Bee Data Extractor")
    print("=" * 50)
    print("\nThis script helps you extract your Spelling Bee game history.")
    print("\nOptions:")
    print("1. Extract from localStorage JSON export")
    print("2. Manual entry (one game at a time)")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    games = []
    
    if choice == '1':
        file_path = input("\nEnter path to localStorage JSON file: ").strip()
        try:
            games = extract_from_localStorage_json(Path(file_path))
            print(f"\n✓ Extracted {len(games)} games")
        except Exception as e:
            print(f"\n✗ Error: {e}")
            return
    
    elif choice == '2':
        while True:
            game = create_manual_entry()
            games.append(game)
            
            another = input("\nAdd another game? (y/n): ").strip().lower()
            if another != 'y':
                break
    
    else:
        return
    
    # Save to JSON
    if games:
        output_file = Path('spelling_bee_raw.json')
        with open(output_file, 'w') as f:
            json.dump(games, f, indent=2)
        
        print(f"\n✓ Saved {len(games)} games to {output_file}")
        print("\nNext step: Run process_data.py to clean and load into database")
    else:
        print("\nNo games extracted.")


if __name__ == '__main__':
    main()

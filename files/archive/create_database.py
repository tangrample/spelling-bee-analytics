#!/usr/bin/env python3
"""
Database schema for NYT Spelling Bee analytics
Creates SQLite database with proper structure
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_FILE = 'spelling_bee.db'

def create_database():
    """Create the database schema."""

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

    # Main games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_date TEXT UNIQUE NOT NULL,
            puzzle_letters TEXT NOT NULL,
            center_letter TEXT NOT NULL,
            score INTEGER NOT NULL,
            max_possible_score INTEGER,
            rank_achieved TEXT,
            is_genius BOOLEAN DEFAULT 0,
            is_queen_bee BOOLEAN DEFAULT 0,
            is_gn4l BOOLEAN DEFAULT 0,
            is_revealed BOOLEAN DEFAULT 0,
            total_words_found INTEGER DEFAULT 0,
            total_possible_words INTEGER,
            created_at_et TEXT,
            updated_at_et TEXT
        )
    """)
    
    # Words found by player
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS words_found (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            points INTEGER NOT NULL,
            is_pangram BOOLEAN DEFAULT 0,
            length INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            UNIQUE(game_id, word)
        )
    """)
    
    # All possible words for each puzzle (optional but useful for analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS puzzle_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            points INTEGER NOT NULL,
            is_pangram BOOLEAN DEFAULT 0,
            length INTEGER NOT NULL,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE,
            UNIQUE(game_id, word)
        )
    """)
    
    # Words missed by player (derived table for easy queries)
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS words_missed AS
        SELECT
            pa.game_id,
            pa.word,
            pa.points,
            pa.is_pangram,
            pa.length,
            g.puzzle_date
        FROM puzzle_answers pa
        LEFT JOIN words_found wf ON pa.game_id = wf.game_id AND pa.word = wf.word
        JOIN games g ON pa.game_id = g.id
        WHERE wf.id IS NULL
    """)
    
    # Create indexes for better query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_puzzle_date ON games(puzzle_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_found_game ON words_found(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_found_word ON words_found(word)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_puzzle_answers_game ON puzzle_answers(game_id)")

    # Data dictionary table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            column_name TEXT NOT NULL,
            description TEXT NOT NULL,
            is_raw BOOLEAN DEFAULT 0,
            UNIQUE(table_name, column_name)
        )
    """)

    # Populate data dictionary
    dictionary_entries = [
        # games table
        ('games', 'id', 'Auto-incrementing primary key for each game record', False),
        ('games', 'puzzle_date', 'Date of the puzzle in YYYY-MM-DD format (from NYT data)', True),
        ('games', 'puzzle_letters', 'All 7 letters in the puzzle (6 outer + 1 center), uppercase', True),
        ('games', 'center_letter', 'The required center letter that must be in every word, uppercase', True),
        ('games', 'score', 'Total points earned by the player in this puzzle', False),
        ('games', 'max_possible_score', 'Maximum possible points for this puzzle (sum of all answer values)', False),
        ('games', 'rank_achieved', 'Rank name from NYT (Beginner/Good Start/Moving Up/Good/Solid/Nice/Great/Amazing/Genius/Queen Bee)', True),
        ('games', 'is_genius', 'Boolean: 1 if player reached Genius level (70%+ of max score)', False),
        ('games', 'is_queen_bee', 'Boolean: 1 if player found all possible words (100%)', False),
        ('games', 'is_gn4l', 'Boolean: 1 if player reached Genius using only 5+ letter words (Genius No 4-Letter)', False),
        ('games', 'is_revealed', 'Boolean: 1 if the puzzle answer key has been revealed by the player', True),
        ('games', 'total_words_found', 'Count of words found by the player', False),
        ('games', 'total_possible_words', 'Count of all possible valid words in the puzzle', False),
        ('games', 'created_at_et', 'Timestamp when this record was created in the database (Eastern Time)', False),
        ('games', 'updated_at_et', 'Timestamp when this record was last updated (Eastern Time)', False),

        # words_found table
        ('words_found', 'id', 'Auto-incrementing primary key for each word record', False),
        ('words_found', 'game_id', 'Foreign key reference to games.id', True),
        ('words_found', 'word', 'The word found by the player, lowercase', True),
        ('words_found', 'points', 'Points earned for this word (1 for 4-letter, length for 5+, +7 for pangrams)', False),
        ('words_found', 'is_pangram', 'Boolean: 1 if word uses all 7 letters in the puzzle', False),
        ('words_found', 'length', 'Number of letters in the word', False),
        ('words_found', 'created_at', 'Timestamp when this word was recorded (UTC)', False),

        # puzzle_answers table
        ('puzzle_answers', 'id', 'Auto-incrementing primary key for each answer record', False),
        ('puzzle_answers', 'game_id', 'Foreign key reference to games.id', True),
        ('puzzle_answers', 'word', 'A valid answer word from the puzzle, lowercase', True),
        ('puzzle_answers', 'points', 'Points this word is worth (1 for 4-letter, length for 5+, +7 for pangrams)', False),
        ('puzzle_answers', 'is_pangram', 'Boolean: 1 if word uses all 7 letters in the puzzle', False),
        ('puzzle_answers', 'length', 'Number of letters in the word', False),
    ]

    for entry in dictionary_entries:
        cursor.execute("""
            INSERT OR REPLACE INTO data_dictionary (table_name, column_name, description, is_raw)
            VALUES (?, ?, ?, ?)
        """, entry)

    conn.commit()
    conn.close()
    
    print(f"✓ Database created: {DATABASE_FILE}")
    print("\nTables created:")
    print("  - games: Main game records")
    print("  - words_found: Words you found")
    print("  - puzzle_answers: All possible words for each puzzle")
    print("  - words_missed: View of words you didn't find")


def verify_database():
    """Verify the database structure."""

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\nDatabase structure:")
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"\n{table_name}:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
    
    conn.close()


if __name__ == '__main__':
    print("Creating Spelling Bee database...")
    create_database()
    verify_database()

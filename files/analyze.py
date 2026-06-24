#!/usr/bin/env python3
"""
Spelling Bee Analytics
Example queries and visualizations for your game history
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATABASE_FILE = 'spelling_bee.db'


def get_connection():
    """Get database connection."""
    return sqlite3.connect(DATABASE_FILE)


def basic_stats():
    """Display basic statistics."""
    conn = get_connection()
    
    print("=" * 60)
    print("SPELLING BEE ANALYTICS")
    print("=" * 60)
    
    # Overall stats
    df_games = pd.read_sql_query("SELECT * FROM games", conn)
    
    if len(df_games) == 0:
        print("\nNo games found in database.")
        conn.close()
        return
    
    print("\n📊 OVERALL STATISTICS")
    print("-" * 60)
    print(f"Total games played: {len(df_games)}")
    print(f"Date range: {df_games['date'].min()} to {df_games['date'].max()}")
    print(f"Total words found: {df_games['total_words_found'].sum()}")
    print(f"Total points scored: {df_games['score'].sum()}")
    print(f"Average score per game: {df_games['score'].mean():.1f}")
    print(f"Average words per game: {df_games['total_words_found'].mean():.1f}")
    
    # Achievements
    print("\n🏆 ACHIEVEMENTS")
    print("-" * 60)
    genius_count = df_games['is_genius'].sum()
    genius_pct = (genius_count / len(df_games)) * 100
    print(f"Genius ranks: {genius_count} ({genius_pct:.1f}%)")
    
    queen_bee_count = df_games['is_queen_bee'].sum()
    queen_bee_pct = (queen_bee_count / len(df_games)) * 100
    print(f"Queen Bee: {queen_bee_count} ({queen_bee_pct:.1f}%)")
    
    gn4l_count = df_games['is_gn4l'].sum()
    gn4l_pct = (gn4l_count / len(df_games)) * 100
    print(f"GN4L (Genius No 4-Letter): {gn4l_count} ({gn4l_pct:.1f}%)")
    
    # Best game
    print("\n⭐ BEST GAMES")
    print("-" * 60)
    best_score = df_games.loc[df_games['score'].idxmax()]
    print(f"Highest score: {best_score['score']} points on {best_score['date']}")
    
    most_words = df_games.loc[df_games['total_words_found'].idxmax()]
    print(f"Most words: {most_words['total_words_found']} words on {most_words['date']}")
    
    # Recent performance
    print("\n📈 RECENT PERFORMANCE (Last 7 days)")
    print("-" * 60)
    df_games['date_dt'] = pd.to_datetime(df_games['date'])
    recent = df_games.nlargest(7, 'date_dt')
    
    for _, game in recent.iterrows():
        genius_marker = "🌟" if game['is_genius'] else "  "
        qb_marker = "👑" if game['is_queen_bee'] else "  "
        print(f"{game['date']}: {game['score']:3d} pts, {game['total_words_found']:2d} words "
              f"{genius_marker} {qb_marker} {game['rank_achieved']}")
    
    conn.close()


def word_analysis():
    """Analyze word patterns."""
    conn = get_connection()
    
    print("\n" + "=" * 60)
    print("WORD ANALYSIS")
    print("=" * 60)
    
    # Most common words found
    df_words = pd.read_sql_query("""
        SELECT word, COUNT(*) as times_found, AVG(points) as avg_points
        FROM words_found
        GROUP BY word
        ORDER BY times_found DESC
        LIMIT 10
    """, conn)
    
    print("\n🔤 TOP 10 WORDS YOU FIND MOST OFTEN")
    print("-" * 60)
    for _, row in df_words.iterrows():
        print(f"{row['word']:20s} - found {row['times_found']} times ({row['avg_points']:.0f} pts)")
    
    # Pangrams
    df_pangrams = pd.read_sql_query("""
        SELECT word, points, g.date
        FROM words_found wf
        JOIN games g ON wf.game_id = g.id
        WHERE is_pangram = 1
        ORDER BY g.date DESC
        LIMIT 10
    """, conn)
    
    if len(df_pangrams) > 0:
        print("\n✨ RECENT PANGRAMS FOUND")
        print("-" * 60)
        for _, row in df_pangrams.iterrows():
            print(f"{row['date']}: {row['word']} ({row['points']} pts)")
    
    # Word length distribution
    df_length = pd.read_sql_query("""
        SELECT length, COUNT(*) as count, AVG(points) as avg_points
        FROM words_found
        GROUP BY length
        ORDER BY length
    """, conn)
    
    print("\n📏 WORD LENGTH DISTRIBUTION")
    print("-" * 60)
    for _, row in df_length.iterrows():
        bar = "█" * int(row['count'] / 10)
        print(f"{row['length']:2d} letters: {row['count']:4d} words {bar}")
    
    conn.close()


def missed_words_analysis():
    """Analyze commonly missed words."""
    conn = get_connection()
    
    df_missed = pd.read_sql_query("""
        SELECT word, COUNT(*) as times_missed, AVG(points) as avg_points
        FROM words_missed
        GROUP BY word
        HAVING times_missed > 1
        ORDER BY times_missed DESC
        LIMIT 15
    """, conn)
    
    if len(df_missed) > 0:
        print("\n" + "=" * 60)
        print("COMMONLY MISSED WORDS")
        print("=" * 60)
        print("\n💡 Words you've missed multiple times:")
        print("-" * 60)
        for _, row in df_missed.iterrows():
            print(f"{row['word']:20s} - missed {row['times_missed']} times ({row['avg_points']:.0f} pts each)")
    
    conn.close()


def streaks_and_trends():
    """Calculate streaks and trends."""
    conn = get_connection()
    
    df_games = pd.read_sql_query("""
        SELECT date, is_genius, score
        FROM games
        ORDER BY date
    """, conn)
    
    if len(df_games) == 0:
        conn.close()
        return
    
    print("\n" + "=" * 60)
    print("STREAKS & TRENDS")
    print("=" * 60)
    
    # Current genius streak
    current_streak = 0
    max_streak = 0
    temp_streak = 0
    
    for is_genius in df_games['is_genius']:
        if is_genius:
            temp_streak += 1
            max_streak = max(max_streak, temp_streak)
        else:
            temp_streak = 0
    
    # Check if current streak is active
    for is_genius in reversed(df_games['is_genius'].values):
        if is_genius:
            current_streak += 1
        else:
            break
    
    print("\n🔥 GENIUS STREAKS")
    print("-" * 60)
    print(f"Current streak: {current_streak} games")
    print(f"Longest streak: {max_streak} games")
    
    # Score trend (last 30 days)
    df_games['date_dt'] = pd.to_datetime(df_games['date'])
    recent_30 = df_games[df_games['date_dt'] >= df_games['date_dt'].max() - timedelta(days=30)]
    
    if len(recent_30) >= 2:
        score_trend = recent_30['score'].diff().mean()
        print("\n📊 SCORE TREND (Last 30 days)")
        print("-" * 60)
        if score_trend > 0:
            print(f"Improving! Average +{score_trend:.1f} points per game")
        elif score_trend < 0:
            print(f"Declining: Average {score_trend:.1f} points per game")
        else:
            print("Stable performance")
    
    conn.close()


def export_to_csv():
    """Export data to CSV for further analysis."""
    conn = get_connection()
    
    # Export games
    df_games = pd.read_sql_query("SELECT * FROM games", conn)
    df_games.to_csv('spelling_bee_games.csv', index=False)
    
    # Export words found
    df_words = pd.read_sql_query("""
        SELECT g.date, wf.word, wf.points, wf.is_pangram, wf.length
        FROM words_found wf
        JOIN games g ON wf.game_id = g.id
        ORDER BY g.date, wf.word
    """, conn)
    df_words.to_csv('spelling_bee_words_found.csv', index=False)
    
    conn.close()
    
    print("\n✓ Exported to CSV files:")
    print("  - spelling_bee_games.csv")
    print("  - spelling_bee_words_found.csv")


def main():
    """Run all analytics."""
    
    if not Path(DATABASE_FILE).exists():
        print("Error: Database not found. Run the data pipeline first.")
        return
    
    basic_stats()
    word_analysis()
    missed_words_analysis()
    streaks_and_trends()
    
    print("\n" + "=" * 60)
    
    export_choice = input("\nExport data to CSV? (y/n): ").strip().lower()
    if export_choice == 'y':
        export_to_csv()
    
    print("\n✨ Analysis complete!")


if __name__ == '__main__':
    main()

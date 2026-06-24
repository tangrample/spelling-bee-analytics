# NYT Spelling Bee Personal Analytics Pipeline

A complete data pipeline to import, store, and analyze your NYT Spelling Bee game history locally.

## 📋 What This Does

- **Imports** your Spelling Bee game history from browser localStorage
- **Stores** data in a local SQLite database with proper structure
- **Calculates** derived metrics like GN4L (Genius No 4-Letter words)
- **Analyzes** your performance with statistics and trends
- **Only imports puzzles you've solved** (as requested)

## 🎯 Data Tracked

### Must-Have (Implemented)
- ✅ Date of puzzle
- ✅ Words you guessed
- ✅ Words you didn't guess
- ✅ Level/rank you reached
- ✅ Point value for each word
- ✅ Total points scored
- ✅ GN4L achievement (Genius without 4-letter words)

### Additional Features
- Pangram tracking
- Genius/Queen Bee achievements
- Word length analysis
- Performance streaks
- Commonly missed words

## 🚀 Quick Start

### Step 1: Extract Your Data

**Option A: Automatic Browser Extract (Recommended)**

1. Go to https://www.nytimes.com/puzzles/spelling-bee
2. Open browser DevTools (press `F12`)
3. Click on the **Console** tab
4. Copy the entire contents of `browser_extract.js`
5. Paste into the console and press Enter
6. A JSON file will download to your Downloads folder

**Option B: Manual Extract**

If the browser script doesn't work, you can use the manual entry tool:

```bash
python3 extract_spelling_bee_data.py
# Choose option 2 for manual entry
```

### Step 2: Create Database

```bash
python3 create_database.py
```

This creates `spelling_bee.db` with the proper schema.

### Step 3: Process & Load Data

Place your downloaded JSON file (or `spelling_bee_raw.json` if manually created) in the same directory, then:

```bash
python3 process_data.py
```

This will:
- Clean and validate the data
- Calculate all derived metrics
- Load into the database
- Skip any puzzles you haven't solved yet

### Step 4: Run Analytics

```bash
python3 analyze.py
```

View your statistics including:
- Overall performance stats
- Achievement counts (Genius, Queen Bee, GN4L)
- Best games
- Recent performance
- Word patterns and trends
- Streaks
- Commonly missed words

## 📊 Database Schema

### `games` table
- Date, letters, center letter
- Score, max possible score
- Rank achieved
- Achievement flags (Genius, Queen Bee, GN4L)
- Word counts

### `words_found` table
- Words you guessed for each game
- Points per word
- Pangram flag
- Word length

### `puzzle_answers` table
- All possible words for each puzzle
- Enables calculation of missed words

### `words_missed` view
- Automatically calculates words you didn't find
- Derived from puzzle_answers minus words_found

## 🔍 Example Queries

Once your data is loaded, you can run custom SQL queries:

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('spelling_bee.db')

# Games where you achieved Queen Bee
df = pd.read_sql_query("""
    SELECT date, score, total_words_found 
    FROM games 
    WHERE is_queen_bee = 1
""", conn)

# Your most commonly found words
df = pd.read_sql_query("""
    SELECT word, COUNT(*) as count
    FROM words_found
    GROUP BY word
    ORDER BY count DESC
    LIMIT 20
""", conn)

# Words you always seem to miss
df = pd.read_sql_query("""
    SELECT word, COUNT(*) as times_missed
    FROM words_missed
    GROUP BY word
    ORDER BY times_missed DESC
    LIMIT 20
""", conn)

conn.close()
```

## 📈 Advanced Analytics

You can create Jupyter notebooks for visualizations:

```python
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3

conn = sqlite3.connect('spelling_bee.db')

# Score over time
df = pd.read_sql_query("""
    SELECT date, score FROM games ORDER BY date
""", conn)

plt.figure(figsize=(12, 6))
plt.plot(pd.to_datetime(df['date']), df['score'])
plt.title('Spelling Bee Score Over Time')
plt.xlabel('Date')
plt.ylabel('Score')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

conn.close()
```

## 🔄 Updating Your Data

As you play new games:

1. Export new data using `browser_extract.js`
2. Run `process_data.py` again
3. The database will update with new games (using `INSERT OR REPLACE`)

## 📁 Files Created

After running the pipeline:

```
spelling_bee.db                      # SQLite database
spelling_bee_raw.json                # Raw exported data
spelling_bee_games.csv               # (Optional) Games export
spelling_bee_words_found.csv         # (Optional) Words export
```

## 🛠️ Customization

### Add Custom Metrics

Edit `process_data.py` to add your own derived calculations:

```python
def calculate_custom_metric(game_data):
    # Your custom logic here
    return metric_value
```

### Custom Analytics

Create your own analysis scripts following the pattern in `analyze.py`:

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('spelling_bee.db')

# Your custom query
df = pd.read_sql_query("""
    SELECT * FROM games WHERE ...
""", conn)

# Your analysis
print(df.describe())

conn.close()
```

## ⚙️ Requirements

- Python 3.7+
- pandas (install: `pip install pandas`)
- SQLite3 (included with Python)

## 🐛 Troubleshooting

**"No games extracted"**
- Make sure you're logged into NYT Spelling Bee when running browser_extract.js
- Try the manual entry option instead

**"Database not found"**
- Run `create_database.py` first

**"Games have no words"**
- The script filters out unsolved puzzles automatically
- This is intentional per your requirements

**localStorage data looks wrong**
- NYT may change their localStorage structure
- Try manual entry as a fallback
- Check the raw JSON to see what keys are available

## 📝 Notes

- **Privacy**: All data stays on your computer
- **Updates**: Run the pipeline regularly to keep data current
- **Backups**: Consider backing up `spelling_bee.db` periodically
- **GN4L Calculation**: Automatically detects if you reached Genius without using any 4-letter words

## 🎓 Learning Opportunities

This pipeline is also a great learning tool:

- See how often you find certain words
- Identify patterns in words you miss
- Track improvement over time
- Compare performance across different letter combinations

## 🤝 Contributing

Feel free to extend this pipeline! Ideas:
- Add visualizations with matplotlib/plotly
- Build a Streamlit dashboard
- Add word difficulty ratings
- Compare against NYT's expected difficulty

---

**Happy analyzing! 🐝**

# QUICK START GUIDE

## 🚀 Get Started in 3 Steps

### 1️⃣ Extract Your Data (One-Time Setup)

Open https://www.nytimes.com/puzzles/spelling-bee in your browser, then:

```javascript
// Press F12 to open DevTools
// Go to Console tab
// Paste the contents of browser_extract.js
// Press Enter
// Save the downloaded file as spelling_bee_raw.json
```

### 2️⃣ Run the Setup

```bash
python3 setup.py
```

This will:
- Create the database
- Process your data
- Show you analytics

### 3️⃣ Explore Your Stats

```bash
python3 analyze.py
```

That's it! 🎉

---

## 🔄 Updating Later

When you play more games:

```bash
# 1. Extract new data (browser_extract.js)
# 2. Process it
python3 process_data.py

# 3. See updated stats
python3 analyze.py
```

---

## 📊 What You'll See

- **Total games played** and date range
- **Total words found** and points scored
- **Achievement rates** (Genius, Queen Bee, GN4L)
- **Best games** by score and word count
- **Recent performance** (last 7 days)
- **Word patterns** (most common, pangrams, length distribution)
- **Missed words** (words you consistently miss)
- **Streaks** (current and longest Genius streaks)
- **Trends** (score improvement over time)

---

## 💡 Pro Tips

**Want to try it first?**
```bash
cp sample_data.json spelling_bee_raw.json
python3 setup.py
```

**Export to Excel/Sheets?**
```python
python3 analyze.py
# Choose 'y' when asked about CSV export
```

**Custom queries?**
```python
import sqlite3
conn = sqlite3.connect('spelling_bee.db')
cursor = conn.cursor()

# Your SQL here
cursor.execute("SELECT * FROM games WHERE is_genius = 1")
print(cursor.fetchall())
```

---

## 🆘 Troubleshooting

**"No data file found"**
→ Extract data using browser_extract.js first

**"Missing pandas"**
→ `pip install pandas`

**"No games in database"**
→ Check that spelling_bee_raw.json has valid data

---

## 📁 Key Files

- `spelling_bee.db` - Your database (back this up!)
- `spelling_bee_raw.json` - Raw data from browser
- `analyze.py` - Run this to see stats
- `README.md` - Full documentation

---

**Questions? Check README.md for detailed documentation!**

# Daily Spelling Bee Data Collection Workflow

## Why Daily Collection?

NYT only keeps **today + yesterday's** puzzle data in localStorage. To build history, you need to capture data daily before yesterday's puzzle disappears.

---

## 🚀 Quick Daily Workflow (2 minutes)

### Option A: Browser Bookmarklet (Easiest)

1. **Create a bookmark** with this code as the URL:

```javascript
javascript:(function(){const d={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k.includes('spelling_bee')||k==='_window_gameData'){d[k]=JSON.parse(localStorage.getItem(k))}}const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='spelling_bee_raw.json';a.click()})();
```

2. **When playing Spelling Bee**, click the bookmark → downloads `spelling_bee_raw.json` automatically

3. **Move the file** to your folder: `/sessions/dreamy-loving-euler/mnt/files/`

4. **Run update script:**
```bash
./update_spelling_bee.sh
```

### Option B: Manual Console Method

1. **Open NYT Spelling Bee**: https://www.nytimes.com/puzzles/spelling-bee
2. **Open DevTools**: Press F12 (or Cmd+Option+I on Mac)
3. **Go to Console tab**
4. **Paste and run this code:**

```javascript
const data = {};
for (let i = 0; i < localStorage.length; i++) {
  const key = localStorage.key(i);
  if (key.includes('spelling_bee') || key === '_window_gameData') {
    data[key] = JSON.parse(localStorage.getItem(key));
  }
}
console.log(JSON.stringify(data, null, 2));
```

5. **Copy the output** → Save to `spelling_bee_raw.json`
6. **Run update script:**
```bash
./update_spelling_bee.sh
```

---

## 📊 What Gets Captured

Each run captures:
- **Today's puzzle** (your progress so far)
- **Yesterday's puzzle** (if revealed, includes answer key)
- Your rank (Genius, Amazing, etc.)
- All words you found
- Total score and points

---

## ⏰ When to Run

**Best time:** Right after you finish playing each day

**Why:** Ensures yesterday's completed puzzle gets saved with full data before it rotates out tomorrow.

**Frequency:** Once per day minimum

---

## 🔮 Future: Automated Scheduling

You chose "manual trigger only" for now. When ready for automation, you can:

1. Set up a daily cron job
2. Use browser automation (Claude in Chrome)
3. Schedule the shortcut to run at 3 AM daily

To enable automation, just ask: *"Set up automatic daily Spelling Bee data collection"*

---

## 📈 Viewing Your Stats

After updating, check your progress:

```bash
# View recent games
sqlite3 spelling_bee.db "SELECT puzzle_date, rank_achieved, score, is_gn4l FROM games ORDER BY puzzle_date DESC LIMIT 10"

# See achievements
sqlite3 spelling_bee.db "SELECT COUNT(*) as genius_days FROM games WHERE is_genius = 1"

# Run full analysis
python3 analyze.py
```

---

## 🛠️ Files in Your Workflow

- `spelling_bee_raw.json` - Raw localStorage data (updated daily)
- `spelling_bee_parsed.json` - Parsed game records
- `spelling_bee.db` - Analytics database (history builds here)
- `update_spelling_bee.sh` - One-command update script
- `parse_nyt_data.py` - Parser (handles raw → structured)
- `process_data.py` - Database loader (adds to history)

---

## 💡 Pro Tips

1. **Don't worry about duplicates** - Database uses INSERT OR REPLACE, safe to re-run
2. **Answer keys hidden for today** - Only revealed puzzles show spoilers
3. **GN4L tracking** - Automatically tracks if you hit Genius using only 5+ letter words
4. **Timestamps in ET** - All times stored in Eastern Time for consistency
5. **Check data dictionary** - Run: `SELECT * FROM data_dictionary` to see what each field means

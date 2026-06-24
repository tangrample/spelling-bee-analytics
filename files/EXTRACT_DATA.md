# Extract NYT Spelling Bee Data

## What Changed (April 2026)

NYT updated their React app and **removed `window.gameData` from the global scope**. The old bookmarklet relied on this variable, so it stopped working. The new `browser_extract.js` (v3) uses 4 fallback methods to find puzzle data even when `window.gameData` is gone.

---

## Step-by-Step Extraction

1. **Go to** https://www.nytimes.com/puzzles/spelling-bee  
2. **Wait for the hive to appear** (puzzle fully loaded, bee animation done)
3. **Open DevTools:** `F12` on Windows/Linux — `Cmd+Option+I` on Mac
4. Click the **Console** tab
5. **Open** `browser_extract.js` in a text editor, **select all**, and **paste** into the console
6. Press **Enter**
7. A file named `spelling_bee_raw_YYYY-MM-DD.json` will download
8. **Rename it** to `spelling_bee_raw.json` and place it in this folder

Then run the pipeline:

```bash
python3 parse_nyt_data.py
python3 process_data.py
```

---

## What the Script Captures

| Data | Source | Notes |
|------|--------|-------|
| Your words found | `localStorage` | Always available |
| Rank achieved | `localStorage` | Always available |
| Letters / center letter | Puzzle metadata | Needs one of 4 methods |
| All possible words | Puzzle metadata | Needs one of 4 methods |
| Pangrams | Puzzle metadata | Needs one of 4 methods |

---

## Troubleshooting

### "Puzzle metadata not found" warning
The script couldn't find the letter/word data. Try these in order:

1. **Refresh the page** and wait 10+ seconds before running the script
2. **Play one word** to ensure the game is fully initialized, then re-run
3. **Use the Network tab approach** (see below)

### Network Tab Approach (most reliable fallback)

If all 4 extraction methods fail, you can capture the data as the page loads:

1. Open DevTools (`F12`)
2. Click the **Network** tab
3. Check **Preserve log**
4. Refresh the page (Cmd+R / Ctrl+R)
5. In the Network filter bar, type: `spelling-bee`
6. Look for requests ending in `.json` or containing puzzle data
7. Click on a matching request, go to **Response**, copy the JSON
8. Paste it into the console as: `window.__puzzleData = <pasted JSON>`
9. Then run `browser_extract.js` — it will find your manually set `window.__puzzleData`

### Script doesn't download anything
- Make sure you're on `nytimes.com/puzzles/spelling-bee` (not a preview or Games app)
- Make sure you're **logged in** to your NYT account
- Check if your browser blocks downloads from the console

---

## Verification

After saving `spelling_bee_raw.json`, verify it has both sections:

```bash
python3 -c "import json; d=json.load(open('spelling_bee_raw.json')); print(list(d.keys()))"
```

You should see both:
- `games-state-spelling_bee/...` ← your game history
- `_window_gameData` ← puzzle metadata

If only the game state key is present, you captured personal data but not puzzle letters/words. The pipeline can still import your answers but won't have full word lists.

---

## Bookmarklet (optional)

For a one-click version, create a browser bookmark with this URL (paste the entire contents of `browser_extract.js`, prefixed with `javascript:`). Note: bookmarklets may be blocked by NYT's Content Security Policy on some browsers. If it doesn't work, use the console method above.

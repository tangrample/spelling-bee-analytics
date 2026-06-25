# Spelling Bee Analytics — Project Notes

## What This Is
A personal analytics pipeline for NYT Spelling Bee game history. Data is extracted from the browser, stored in a local SQLite database, and analyzed for performance trends.

## Current State (as of June 25, 2026)
- **110 games** in the database, covering 2026-02-07 to 2026-06-23 with some gaps
- **3,753 words found**, **4,678 puzzle answers** tracked
- **104 of 110 games** have full puzzle_answers data (6 expired before extraction)
- Manual workflow is working on new MacBook
- No automation yet (deliberately avoided due to macOS security tradeoffs)
- **GitHub Pages dashboard live** at `https://tangrample.github.io/spelling-bee-analytics`

## Key Paths
| Thing | Path |
|-------|-------|
| Project folder | `~/Desktop/AI-projects/spelling-bee-analytics/` |
| Scripts | `~/Desktop/AI-projects/spelling-bee-analytics/files/` |
| Database | `~/Desktop/AI-projects/spelling-bee-analytics/files/spelling_bee.db` |
| iCloud drop folder | `~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Spelling Bee/` |

## Daily Workflow
**iPhone → Mac:**
1. Finish playing, reveal answers on iPhone
2. Tap **🐝 Save Bee Data** bookmarklet in Safari
3. File saves to iCloud Drive → Downloads → Spelling Bee
4. On Mac, run `bee` in Terminal — picks up all accumulated iCloud files automatically

**Mac only (alternative):**
1. Go to nytimes.com/puzzles/spelling-bee in Safari
2. Click **🐝 Copy Bee Data** bookmarklet (copies to clipboard)
3. Run `bee` in Terminal

## The `bee` Command
Alias defined in `~/.zshrc`, points to `files/bee_sync.sh`.

Checks data sources in order:
1. Clipboard (from Mac bookmarklet)
2. `~/Downloads/spelling_bee_*.json` (legacy)
3. iCloud Drive folder (from iPhone bookmarklet)

```bash
bee             # smart sync
bee --force     # save all puzzles with any progress
bee --status    # preview without saving
```

## Database Schema
**`games`** — one row per puzzle played
- `id`, `puzzle_date`, `puzzle_letters`, `center_letter`
- `score`, `max_possible_score`, `rank_achieved`
- `is_genius`, `is_queen_bee`, `is_gn4l`, `is_revealed`
- `total_words_found`, `total_possible_words`

**`words_found`** — words you guessed
- `id`, `game_id`, `word`, `points`, `is_pangram`, `length`

**`puzzle_answers`** — all possible words for each puzzle
- `id`, `game_id`, `word`, `points`, `is_pangram`, `length`

**`words_missed`** — view, derived from puzzle_answers minus words_found

## Known Issues / Limitations
- Many games missing entirely — data collection only started 2026-02-07, all prior history is unrecoverable from NYT
- 6 games missing from `puzzle_answers` (puzzles expired before extraction — data unrecoverable)
- `bee_sync_error.log` has old errors from previous laptop with wrong paths — can be ignored
- Automation (launchd folder watcher) was deliberately skipped due to macOS Full Disk Access security requirements

## Bookmarklet Setup Files
- Mac Safari: `files/mac_bookmarklet.html` — open in Safari, drag yellow button to bookmarks bar
- iPhone Safari: `files/iphone_bookmarklet_setup.html` — open on iPhone, follow 4-step setup

## GitHub Pages Dashboard
Live at: `https://tangrample.github.io/spelling-bee-analytics`
Source: `docs/` folder on `main` branch (Settings → Pages → Deploy from branch → main / docs)

**Key files:**
- `docs/index.html` — carousel dashboard (div-based charts, fetches data.json)
- `docs/data.json` — exported by `files/export_analytics.py`, auto-committed by `bee_sync.sh`
- `docs/bee.svg` — nerd bee SVG used as favicon (SVG favicon; note: flaky in some browsers)
- `files/export_analytics.py` — reads SQLite DB, writes data.json with summary, recent (last 7 days), monthly stats, miss-by-length, study words (top 100 weighted + last_missed date), missed pangrams

**Dashboard design:** 5-slide carousel, clean/calm aesthetic.
- Slide 1 — Overview: this-week stats (score %, miss rate, genius, pangrams) with all-time below
- Slide 2 — Words to study: Recent section (missed in last 7 days) pinned above All-time list
- Slide 3 — Missed pangrams
- Slide 4 — Monthly trend: div-based grouped bar chart (score % + words found %), scale 60–90%, hover tooltips
- Slide 5 — Miss rate by word length

**Navigation:** dot indicators + prev/next arrows + keyboard arrows + touch swipe

**Header:** "BeeBot" with inline SVG of two fist-bumping bees — floppy sun hat (left) + red beanie with pompom (right). Arms raised upward to meet in the middle.

**Favicon:** `docs/bee.svg` — single nerd bee with round glasses. Referenced via `<link rel="icon" type="image/svg+xml" href="bee.svg">`. SVG favicon support is browser-dependent; may not show in all browsers.

**Footer:** "Reflects data from N puzzles (date – date). Word miss stats exclude N games with incomplete data."

**Auto-update flow:** `bee` → `smart_update.py` → `export_analytics.py` → `git commit + push` → Pages rebuilds in ~1 min.

## What's Next
- [ ] Consider adding word definitions to more study words (expand DEFINITIONS dict in export_analytics.py)
- [ ] Consider daily/weekly word push notification (e.g. email or widget) for study words
- [ ] Favicon: convert bee.svg to PNG/ICO for reliable cross-browser support

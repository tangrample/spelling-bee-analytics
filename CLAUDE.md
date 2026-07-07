# Spelling Bee Analytics — Project Notes

## What This Is
A personal analytics pipeline for NYT Spelling Bee game history. Data is extracted from the browser, stored in both a local SQLite database and Supabase (Postgres), and analyzed for performance trends.

## Current State (as of July 7, 2026)
- **Trend chart x-axis labels fixed:** the weekly/monthly label thinning logic (`TrendChart` in `Dashboard.tsx`) previously force-included the last data point regardless of how close it landed to the last regularly-spaced label, which could crowd the two together (e.g. 7/6 landing right on top of 6/29 on mobile). Now uses a plain constant index step with no special-casing of the last point — it's only labeled if it happens to fall on the step, same as any other point. This keeps spacing uniform at the cost of not always labeling the most recent point.
- **Study words list logic changed:** `study_words` (`analytics.ts`) no longer requires `appearances >= 2` — a word missed on its only appearance so far now qualifies, since the goal is general vocab building, not just flagging repeat spelling-bee weak spots. Also now excludes pangrams entirely (they already have their own "Missed pangrams" card). To make sure a fresh miss can't be buried by its own low weight, `study_words` is no longer capped in `analytics.ts` — `Dashboard.tsx` instead applies the top-100 cap only to the "all time" bucket, after splitting out anything missed in the last 7 days; the "Recent" bucket is never capped.
- **Word definition quality fixes:**
  - Added a Datamuse (WordNet-backed) fallback lookup for words dictionaryapi.dev (Wiktionary-backed) doesn't have — e.g. regularly-formed but uncommon derivations like "hateable"/"healable". Datamuse's `sp=` param is a *fuzzy* spelled-like search, not an exact match, so the fallback requires the returned word to match the query exactly (case-insensitive) before accepting a definition — otherwise it can silently return a different word's definition (verified this actually happens: querying "anagramming" returns "diagramming"'s definition, "idylically" returns "idyllically"'s). Words with no exact match anywhere still show the generic "N-letter word" fallback, which is intentional/correct, not a bug.
  - Both lookup functions now filter out low-quality definitions (`isLowQualityDefinition` — anything under 15 characters, plus a light explicit-content denylist) and scan all senses across all meanings for the first one that passes, rather than grabbing whatever sense the API lists first. Wiktionary/WordNet don't order by "most useful" — e.g. "adorn" listed a bare one-word noun sense ("Adornment") before its actual verb definition, and "anal" listed an obscure reptile-anatomy noun sense (plus a vulgar one) before its common adjective senses.
  - `anal` and `adorn` also got manual overrides in the `DEFINITIONS` dict, since they were already cached in Supabase with the bad pre-filter values — a hardcoded entry always takes priority over the cache, so this fixes them immediately without touching the database. Worth spot-checking other already-cached words for similar quality issues if you notice more.
- **Git regression from the stale index, found and fixed:** the stale/corrupted index flagged in "Agent sandbox + git" below wasn't just cosmetic — since `git commit` always commits the *entire* index (not just explicitly `git add`ed paths), the first commit made this session silently reverted every tracked file the stale index still had a wrong entry for, even though only two files were explicitly staged. Confirmed casualties: `files/mac_bookmarklet.html` got reverted from the sync-first fix back to the old download-first-then-sync code (re-introducing the iPhone sync bug), `files/iphone_bookmarklet_setup.html` got resurrected in the repo despite being deleted on disk, and `docs/data.json` got reverted to a stale July 5 snapshot. All three were re-committed from the correct on-disk working tree state to fix it. **Lesson: after clearing the stale-lock files per the workaround below, always run `git status`/`git diff HEAD --stat` for the *whole* repo before the next commit, not just the files you meant to touch** — a stale index can quietly revert anything.
- **Carousel slide-width bug fixed:** `.slide` in `globals.css` only had `min-width: 100%` with no upper bound, so a row with an unusually long word definition (which also wasn't wrapping, due to a classic flex `min-width` default gotcha on `.word-def`) could force the whole slide wider than the viewport — `carousel-outer`'s `overflow: hidden` clipped it visually but the extra width still existed in the layout, so swiping into that slack looked like "sliding into blank space." Fixed by adding `max-width: 100%` to `.slide`, and giving `.word-def` `min-width: 0` + `max-width: 60%` + `overflow-wrap: break-word` so long definitions wrap onto multiple lines within their row instead of forcing the row (and slide) wider.

## Previous State (as of July 6, 2026)
- **Bookmarklet setup simplified:** dropped the separate iPhone bookmarklet in favor of relying on iCloud Safari bookmark sync — add/edit only the Mac bookmarklet (`files/mac_bookmarklet.html`), and it syncs to iPhone's bookmarks list automatically (requires Safari toggled on under iCloud settings on both devices). `files/iphone_bookmarklet_setup.html` has since been deleted.
- **Bookmarklet script reordered:** cloud sync (`fetch` to `/api/sync`) now runs *before* the file download is triggered, not after. On iPhone, tapping the bookmarklet's download link shows an OS-level "Do you want to download...?" interstitial that can interrupt page JS before an async `.then()` fires — so with the old order, the sync silently never completed on iPhone even though the download succeeded. Sync-first fixes this for both platforms.
- **122 games** in Supabase as of Jul 7 (dashboard header), covering 2026-02-07 to 2026-07-06 with some gaps — SQLite count may lag behind since it only updates when `bee` is run locally, whereas Supabase updates live via the bookmarklet
- **~110-116 games** (may have grown alongside the count above) have full puzzle_answers data — 6 expired before extraction and are permanently missing that data (see Known Issues)
- **Phase 1 complete:** cloud pipeline live — bookmarklet POSTs to Supabase, dashboard on Vercel
- Local Mac workflow still works as fallback (SQLite + GitHub Pages)
- **Branding pass done:** Vercel dashboard now has custom bee icon/favicon, page title "BeeBot", and a fan-project disclaimer in the footer (not affiliated with/endorsed by NYT)
- **Trend chart redesigned:** the old monthly bar chart is now a line chart (`TrendChart` in `Dashboard.tsx`) with a Weekly/Monthly toggle (defaults to weekly), a fixed 0-100 y-axis with nice ticks (auto-widens if scores drop), and a custom hover tooltip — native SVG `<title>` tooltips don't render reliably in Safari, which this project requires. The chart also measures its own rendered pixel size (`ResizeObserver`) so text doesn't shrink illegibly on narrow phone screens.
- **Word-length miss-rate chart** (last carousel slide) now has a "7 games / 30 games / All time" toggle, defaulting to All time. Windows are game-count-based, not calendar-day-based, consistent with how "recent" is computed everywhere else (see Known Issues).
- **Mobile overview-card fix:** stat numbers no longer wrap onto a second line (`white-space: nowrap` + smaller font at ≤600px), and row spacing was opened up so the 2x2 grid better fills the card height.
- **Security:** `files/migrate_to_supabase.py` (one-off migration script) contained a hardcoded Supabase service_role key and has been deleted. The key was rotated in Supabase (Settings → API Keys → Secret keys) and updated in Vercel's `SUPABASE_SERVICE_ROLE_KEY` env var. It was never committed to git history. Also removed `files/fix_jun28.py` (one-time data patch, already applied).
- **Length-slide takeaway is now dynamic:** the hardcoded "Mostly cheap losses — 4-letter words..." line on the last carousel card (`LengthSlide` in `Dashboard.tsx`) has been replaced with a computed insight — whichever word length currently has the highest miss rate for the selected range — and renders nothing if there's nothing to report.
- **Word definitions — live:** `word_definitions` Supabase table (schema in `files/add_word_definitions_table.sql`) has been created and is in use, caching definitions from the free dictionaryapi.dev API instead of relying solely on the small hand-curated `DEFINITIONS` dict in `web/lib/analytics.ts` (~65 entries vs. 433 words that actually qualify as study words — hence the old "4-letter word" fallbacks). `analytics.ts` reads the cache, falls back to the hardcoded dict, and auto-fetches + caches any still-missing definition for words in the visible top-100 study words going forward (self-maintaining, bounded, 3s timeout per lookup so a slow API can't stall the dashboard). Confirmed live on the deployed dashboard — dictionary-backed definitions are showing and the old hardcoded fallback text is gone.
  - `files/add_word_definitions_table.sql` and `files/backfill_definitions.py` are one-off scripts (schema creation + optional backfill) — safe to delete once you've confirmed the backfill has run, same convention as other one-off scripts in this repo. They're currently untracked in git; commit or delete them rather than leaving them dangling.

## Key Paths
| Thing | Path |
|-------|-------|
| Project folder | `~/Desktop/AI-projects/spelling-bee-analytics/` |
| Scripts | `~/Desktop/AI-projects/spelling-bee-analytics/files/` |
| Database | `~/Desktop/AI-projects/spelling-bee-analytics/files/spelling_bee.db` |
| Web app | `~/Desktop/AI-projects/spelling-bee-analytics/web/` |
| iCloud drop folder | `~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Spelling Bee/` |

## Daily Workflow (Cloud — preferred)
**iPhone:**
1. Finish playing, reveal answers in Safari
2. Tap **🐝 Save Bee Data** bookmarklet
3. File saves to iCloud AND syncs to Supabase — dashboard updates automatically

**Mac:**
1. Go to nytimes.com/puzzles/spelling-bee in Safari
2. Click **🐝 Save Bee Data** bookmarklet
3. Downloads a dated file to `~/Downloads`, copies to clipboard, AND syncs to Supabase — no `bee` command needed

## Daily Workflow (Local fallback)
Same as above, but also run `bee` in Terminal to write to SQLite and update GitHub Pages. `bee` picks up every `spelling_bee_*.json` sitting in `~/Downloads` (oldest first) each time it runs, so it's fine to skip it for several days — the files just accumulate until you run it. (As of Jul 2026, the Mac bookmarklet is named **Save Bee Data**, not Copy Bee Data — it downloads a file instead of relying on clipboard, since clipboard content only lasts until you copy something else.)

## The `bee` Command
Alias defined in `~/.zshrc`, points to `files/bee_sync.sh`.

```bash
bee             # smart sync
bee --force     # save all puzzles with any progress
bee --status    # preview without saving
```

## Bookmarklet Setup Files
- Mac Safari: `files/mac_bookmarklet.html` — open in Safari, drag yellow button to bookmarks bar. This is now the *only* bookmarklet to maintain — it syncs to iPhone via iCloud Safari bookmark sync, no separate iPhone setup needed.
- `files/iphone_bookmarklet_setup.html` — deleted (was legacy/unused; manually recreating the bookmarklet on iPhone instead of relying on sync was the original source of the Mac/iPhone mismatch bug).
- The bookmarklet POSTs to `/api/sync` on Vercel (sync-first, then triggers file download — see Current State above)

## Cloud Infrastructure
| Thing | Value |
|-------|-------|
| Supabase project | `https://keeizqtabnmpjdbuwxoj.supabase.co` |
| Vercel dashboard | `https://spelling-bee-analytics.vercel.app` |
| Vercel repo | `tangrample/spelling-bee-analytics`, root dir `web/` |
| Sync endpoint | `POST https://spelling-bee-analytics.vercel.app/api/sync` |

**Environment variables in Vercel:**
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SYNC_SECRET`

**Key web app files:**
- `web/app/page.tsx` — server component, fetches analytics from Supabase
- `web/components/Dashboard.tsx` — client component, carousel UI (header icon, title, footer disclaimer, `TrendChart` line chart, `LengthSlide` miss-rate chart)
- `web/lib/analytics.ts` — all analytics computations (port of export_analytics.py). Computes `weekly`/`monthly` stats (calendar-bucketed, ISO weeks Mon–Sun) for the trend chart, and `miss_by_length` as three ranges (`last7`/`last30`/`all`, game-count-based) for the length chart
- `web/lib/parseNYTData.ts` — parses raw bookmarklet JSON (port of parse_nyt_data.py + process_data.py)
- `web/app/api/sync/route.ts` — accepts POST from bookmarklet, upserts to Supabase
- `web/app/layout.tsx` — page metadata (title: "BeeBot")
- `web/app/icon.png`, `web/app/apple-icon.png`, `web/app/favicon.ico` — bee icon, auto-wired by Next.js App Router (no manual `<link>` tags needed)

## Database Schema (SQLite + Supabase, identical structure)
**`games`** — one row per puzzle played
- `id`, `puzzle_date`, `puzzle_letters`, `center_letter`
- `score`, `max_possible_score`, `rank_achieved`
- `is_genius`, `is_queen_bee`, `is_gn4l`, `is_revealed`
- `total_words_found`, `total_possible_words`
- `user_id` (Supabase only, NULL for Phase 1 — used in Phase 2 for multi-user)

**`words_found`** — words you guessed
- `id`, `game_id`, `word`, `points`, `is_pangram`, `length`

**`puzzle_answers`** — all possible words for each puzzle
- `id`, `game_id`, `word`, `points`, `is_pangram`, `length`

**`words_missed`** — view, derived from puzzle_answers minus words_found

**Supabase note:** `games` has a partial unique index on `puzzle_date WHERE user_id IS NULL` (instead of a standard UNIQUE constraint) to handle NULL user_ids correctly in Phase 1.

## GitHub Pages Dashboard (legacy, still live)
Live at: `https://tangrample.github.io/spelling-bee-analytics`
Updated by `bee` → `export_analytics.py` → `git push`. Will be superseded by Vercel app.

## Known Issues / Limitations
- 6 games missing from `puzzle_answers` (puzzles expired before extraction — data unrecoverable)
- `bee_sync_error.log` has old errors from previous laptop — can be ignored
- Vercel dashboard reads live from Supabase; local SQLite and GitHub Pages are independent and only updated when `bee` is run manually
- **Agent sandbox + git:** this project folder has delete-protection that blocks the Claude sandbox from unlinking files in it. Git's own internal cleanup of lock/temp files (`.git/index.lock`, `.git/HEAD.lock`, `.git/objects/*/tmp_obj_*`) hits this and leaves stray files behind after every commit. This is **not purely cosmetic**: a stray `.git/index.lock` blocks any further commit attempt from the sandbox, and a partially-written `.git/index` left over from an interrupted commit can make `git diff` / `git status` (which compare working tree → index) show phantom "pending changes" for content that's actually already committed and pushed — always cross-check with `git diff HEAD` (working tree → HEAD, skips the index) and `git show origin/main:<path>` before trusting `git status` output in this repo. Workaround for running git from the agent sandbox: point the index outside the mount, e.g. `GIT_INDEX_FILE=/tmp/sb_index git read-tree HEAD && GIT_INDEX_FILE=/tmp/sb_index git add -A && GIT_INDEX_FILE=/tmp/sb_index git commit -m "..."`. `git push` itself doesn't need the index and works normally once a real GitHub credential/SSH key is available (the agent sandbox doesn't have one — push from the user's own Terminal instead). Cleanup from the user's Mac Terminal (recommended after any sandbox commit attempt, not just optional): `rm -f .git/index.lock .git/HEAD.lock .git/objects/*/tmp_obj_* && git status` to reset the index to a clean state.
- "Recent" stats (overview slide, 7/30-game miss-rate windows) are defined by **game count, not calendar days** — e.g. "last 7" means the 7 most recent games played, not the last 7 calendar days. This is intentional: calendar-day windows would shrink unpredictably whenever days are skipped. The trend chart's Weekly/Monthly toggle is the one exception — it's genuinely calendar-bucketed (ISO weeks/months) since its whole purpose is showing change over real time, including gaps in play as silently-omitted (not specially flagged) points

## What's Next (Phase 2)
- [ ] Add Supabase Auth (email magic link)
- [ ] Landing page + onboarding flow for bookmarklet install
- [ ] Tighten RLS policies to user_id-scoped access
- [ ] Add `user_id NOT NULL` constraint once auth is wired up
- [ ] Push notifications via email for study words
- [ ] Consider adding word definitions (expand DEFINITIONS dict in `web/lib/analytics.ts`)

## Product Direction
**Goal:** Shareable web product, passion project, no monetization pressure.

**Architecture:**
- **Backend:** Supabase (Postgres + auth, free tier)
- **Frontend:** Next.js on Vercel
- **Data ingestion:** Bookmarklet POSTs raw localStorage JSON to `/api/sync`, parsed server-side

**Key constraints:**
- Safari is a hard requirement — bookmarklet reads JS state from the NYT page. Native app is a black box.
- `puzzle_answers` is stored (it's publicly available data on misc sites, low ToS risk)

**Phased plan:**
- **Phase 1** ✅ — Cloud pipeline live. Supabase + Vercel + updated bookmarklets. No Mac required for daily workflow.
- **Phase 2** — Multi-user auth, landing page, onboarding.
- **Phase 3** — Polish, email notifications, cross-browser testing.

**What to tell users:** "Requires playing in Safari (mobile or desktop). Native NYT app not supported."

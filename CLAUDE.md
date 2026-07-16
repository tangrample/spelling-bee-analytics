# Spelling Bee Analytics — Project Notes

## What This Is
A personal analytics pipeline for NYT Spelling Bee game history. Data is extracted from the browser via a Safari bookmarklet, stored in Supabase (Postgres), and analyzed for performance trends on a Next.js dashboard.

## Current State (as of July 16, 2026)
- **Local SQLite/GitHub Pages pipeline retired.** Now that the cloud pipeline (bookmarklet → Supabase → Vercel dashboard) has been validated as the sole daily driver for months, the local fallback path was retired as redundant maintenance overhead — it had its own parsing logic (`parse_nyt_data.py`/`process_data.py`) duplicating the web app's TS port, and had already drifted out of sync in a real way (local `smart_update.py` silently skips re-saving a puzzle_date that's already in SQLite, while the Supabase sync route upserts and reflects the latest download — found while investigating why local counts lagged Supabase).
  - Retired/archived (moved to `files/archive/`, not deleted, in case anything needs to be referenced later): `bee_sync.sh`, `smart_update.py`, `export_analytics.py`, `create_database.py`, `process_data.py`, `parse_nyt_data.py`, `bee_orchestrate.py`, `spelling_bee.db`, `spelling_bee_raw.json`, `bee_sync.log`, `bee_sync_error.log`, `install_bee.sh`, `install_schedule.sh`, `Update Spelling Bee.command`. The GitHub Pages site (`docs/index.html`, `docs/data.json`, `docs/bee.svg`) was archived to `files/archive/docs_github_pages/`.
  - The `bee` alias in `~/.zshrc` was **not** removed by this pass (out of reach from the agent sandbox — home directory outside the mounted project folder). Remove it yourself whenever convenient; it's harmless if left (just points at an archived script and will error if run).
  - `files/mac_bookmarklet.html` simplified to cloud-sync-only — dropped the "download a dated file to ~/Downloads" step and its clipboard-copy fallback, since nothing consumes that file anymore. It now just POSTs to `/api/sync` and shows a success/failure alert. Re-drag the bookmark from the updated file if you want the simplified version (the old one in your Safari bookmarks bar still works fine as-is, it'll just keep downloading files nobody reads).
  - Replaced the SQLite mirror with a weekly scheduled Cowork task (`spelling-bee-supabase-backup`, Sundays) that exports all four Supabase tables (`games`, `words_found`, `puzzle_answers`, `word_definitions`) to a dated JSON snapshot at `files/backups/backup_<date>.json`, purely as an off-Supabase safety net — not a live mirror, not queried by anything, just a periodic restore point. Old snapshots beyond 90 days are pruned automatically. Runs silently unless something breaks.
  - Net effect: Supabase is now the only source of truth. No more `bee` command, no more manually remembering to run it, no more two copies of parsing logic to keep in sync.
  - GitHub Pages fully disabled (not just source-archived): Settings → Pages → source set to "None" on the GitHub repo. This also stops the `pages build and deployment` GitHub Action from running (and failing/emailing) on every push now that `docs/` is empty — it was still trying to build an empty folder until this was set.
- **Queen Bee now implies revealed.** `web/lib/parseNYTData.ts` previously only saved `puzzle_answers` when NYT's own `isRevealed` flag was true, which meant a Queen Bee game (100% — every word found) synced *before* tapping "reveal" would silently miss its answer-key data, even though finding every word means the answer key is already fully known. Fixed by computing `effectivelyRevealed = isRevealed || isQueenBee` and using that everywhere `is_revealed`/`puzzleAnswers` are set. Confirmed only one existing game was affected (2026-07-16, that day's Queen Bee) — re-syncing it after deploy backfilled its answers correctly; all other historical Queen Bee games already had `is_revealed: true` regardless. Not retroactive — only affects games synced after this deployed (commit `ccda8a2`).
- **Querying Supabase directly (e.g. DBeaver):** the direct connection host (`db.<ref>.supabase.co:5432`) is IPv6-only in this region and fails with "No route to host" on networks without IPv6 routing. Use the **Session pooler** instead (Supabase dashboard → Connect → Direct tab → toggle "Display connection pooler" → Session pooler) — get the exact host/port from that dialog rather than guessing the region-based hostname (transaction pooler works for stateless queries but breaks GUI-client session state; session pooler behaves like a normal persistent connection). Username for the pooler is `postgres.<project-ref>`, not just `postgres`. SSL mode should be `require` (not `verify-full`) or DBeaver will look for a local root cert file that doesn't exist and fail to connect.

## Previous State (as of July 7, 2026)
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
| Retired local pipeline (archived) | `~/Desktop/AI-projects/spelling-bee-analytics/files/archive/` |
| Off-Supabase backups | `~/Desktop/AI-projects/spelling-bee-analytics/files/backups/` |
| Web app | `~/Desktop/AI-projects/spelling-bee-analytics/web/` |
| iCloud drop folder | `~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/Spelling Bee/` (legacy, unused now that the bookmarklet is cloud-sync-only) |

## Daily Workflow (Cloud-only)
**iPhone:**
1. Finish playing, reveal answers in Safari
2. Tap **🐝 Save Bee Data** bookmarklet
3. Syncs to Supabase — dashboard updates automatically

**Mac:**
1. Go to nytimes.com/puzzles/spelling-bee in Safari
2. Click **🐝 Save Bee Data** bookmarklet
3. Syncs to Supabase — dashboard updates automatically

That's it — no `bee` command, no Downloads folder cleanup, nothing else to run. (See "Local SQLite/GitHub Pages pipeline retired" above for why this used to be more involved.)

## Bookmarklet Setup Files
- Mac Safari: `files/mac_bookmarklet.html` — open in Safari, drag yellow button to bookmarks bar. This is the *only* bookmarklet to maintain — it syncs to iPhone via iCloud Safari bookmark sync, no separate iPhone setup needed.
- `files/iphone_bookmarklet_setup.html` — deleted (was legacy/unused; manually recreating the bookmarklet on iPhone instead of relying on sync was the original source of the Mac/iPhone mismatch bug).
- The bookmarklet POSTs to `/api/sync` on Vercel and shows a success/failure alert — that's its entire job now (no download step, no clipboard copy — see Current State above).

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

## Database Schema (Supabase — Postgres only, SQLite retired)
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

## GitHub Pages Dashboard (retired)
Was live at `https://tangrample.github.io/spelling-bee-analytics`, updated by `bee` → `export_analytics.py` → `git push`. Retired alongside the rest of the local pipeline (see Current State) — the Vercel dashboard reading live from Supabase is now the only dashboard. The GitHub Pages repo content itself (the actual published site, separate from this local `docs/` source) hasn't been un-published — if you want it fully gone, disable Pages in the GitHub repo settings.

## Known Issues / Limitations
- 6 games missing from `puzzle_answers` (puzzles expired before extraction — data unrecoverable). A 7th (today's game) will always transiently show as missing until it's revealed (or Queen Bee'd, see Current State) and re-synced — not a bug.
- `files/archive/bee_sync_error.log` has old errors from previous laptop — can be ignored
- Vercel dashboard reads live from Supabase, which is now the sole source of truth. `files/backups/` holds periodic off-Supabase snapshots (weekly scheduled task) purely as a restore point, not a live mirror.
- **Agent sandbox + git:** this project folder has delete-protection that blocks the Claude sandbox from unlinking files in it. Git's own internal cleanup of lock/temp files (`.git/index.lock`, `.git/HEAD.lock`, `.git/objects/*/tmp_obj_*`) hits this and leaves stray files behind after every commit. This is **not purely cosmetic**: a stray `.git/index.lock` blocks any further commit attempt from the sandbox, and a partially-written `.git/index` left over from an interrupted commit can make `git diff` / `git status` (which compare working tree → index) show phantom "pending changes" for content that's actually already committed and pushed — always cross-check with `git diff HEAD` (working tree → HEAD, skips the index) and `git show origin/main:<path>` before trusting `git status` output in this repo. Workaround for running git from the agent sandbox: point the index outside the mount, e.g. `GIT_INDEX_FILE=/tmp/sb_index git read-tree HEAD && GIT_INDEX_FILE=/tmp/sb_index git add -A && GIT_INDEX_FILE=/tmp/sb_index git commit -m "..."`. `git push` itself doesn't need the index and works normally once a real GitHub credential/SSH key is available (the agent sandbox doesn't have one — push from the user's own Terminal instead). Cleanup from the user's Mac Terminal (recommended after any sandbox commit attempt, not just optional): `rm -f .git/index.lock .git/HEAD.lock .git/objects/*/tmp_obj_* && git status` to reset the index to a clean state.
- "Recent" stats (overview slide, 7/30-game miss-rate windows) are defined by **game count, not calendar days** — e.g. "last 7" means the 7 most recent games played, not the last 7 calendar days. This is intentional: calendar-day windows would shrink unpredictably whenever days are skipped. The trend chart's Weekly/Monthly toggle is the one exception — it's genuinely calendar-bucketed (ISO weeks/months) since its whole purpose is showing change over real time, including gaps in play as silently-omitted (not specially flagged) points

## What's Next (Phase 2)
**Deprioritized as of July 8, 2026.** Discussed and decided Phase 2 (multi-user auth) isn't worth building preemptively. Reasoning: user expects to remain the primary/only user for the foreseeable future, and magic-link auth would make their *own* daily experience worse — session expiry requiring re-login, and (more importantly) the bookmarklet would need to carry a per-user token that can expire/break, turning data *sync* failures (not just dashboard-viewing failures) into a real risk. That's a worse failure mode than today's shared-secret POST.

If someone else does want in before real multi-tenant auth is built, the lighter-weight fallback is to clone the whole stack for them (their own Supabase project + Vercel deployment + env vars + bookmarklet pointing at their own sync endpoint) rather than adding login. That avoids any new friction for the existing user, at the cost of a one-time per-person setup (30-60 min, either self-serve for a technical friend or done on their behalf) instead of a centralized shared deployment.

Revisit Phase 2 only when there's concrete demand from a real second user, not before. Original scope, if/when it happens:
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
- Safari is a hard requirement — bookmarklet reads JS state from the NYT page. Native app is a black box (no way to inject code like the bookmarklet does).
- `puzzle_answers` is stored (it's publicly available data on misc sites, low ToS risk)
- **Known unknown (July 8, 2026):** NYT Games syncs play progress to your NYT account across devices, which implies some backend API for it — there's precedent for scraping personal stats this way (e.g. `kesyog/crossword` on GitHub uses NYT's undocumented crossword-stats REST API via the account session cookie). Unconfirmed whether Spelling Bee's equivalent endpoint (if it exists) exposes per-word data (`words_found`/`puzzle_answers`) or just aggregate stats (streak/score), and building it would mean capturing + maintaining an auth token rather than the bookmarklet's one-off localStorage read — likely higher risk, not lower friction, unless the current daily bookmarklet click becomes an actual pain point. Not pursued unless that changes.

**Phased plan:**
- **Phase 1** ✅ — Cloud pipeline live. Supabase + Vercel + updated bookmarklets. No Mac required for daily workflow. The local SQLite/GitHub Pages fallback that existed alongside this during validation has since been retired (July 16, 2026) — cloud is now the only path, not just the preferred one.
- **Phase 2** — Multi-user auth, landing page, onboarding. Deprioritized as of July 8, 2026 — see "What's Next (Phase 2)" for reasoning; only revisit if a real second user wants in.
- **Phase 3** — Polish, email notifications, cross-browser testing.

**What to tell users:** "Requires playing in Safari (mobile or desktop). Native NYT app not supported."

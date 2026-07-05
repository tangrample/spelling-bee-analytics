# Spelling Bee Analytics — Project Notes

## What This Is
A personal analytics pipeline for NYT Spelling Bee game history. Data is extracted from the browser, stored in both a local SQLite database and Supabase (Postgres), and analyzed for performance trends.

## Current State (as of July 4, 2026)
- **116 games** in SQLite and Supabase, covering 2026-02-07 to 2026-06-29 with some gaps
- **110 of 116 games** have full puzzle_answers data (6 expired before extraction)
- **Phase 1 complete:** cloud pipeline live — bookmarklet POSTs to Supabase, dashboard on Vercel
- Local Mac workflow still works as fallback (SQLite + GitHub Pages)
- **Branding pass done:** Vercel dashboard now has custom bee icon/favicon, page title "BeeBot", and a fan-project disclaimer in the footer (not affiliated with/endorsed by NYT)

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
- Mac Safari: `files/mac_bookmarklet.html` — open in Safari, drag yellow button to bookmarks bar
- iPhone Safari: `files/iphone_bookmarklet_setup.html` — open on iPhone, follow 4-step setup
- Both bookmarklets now POST to `/api/sync` on Vercel in addition to their existing behavior

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
- `web/components/Dashboard.tsx` — client component, carousel UI (header icon, title, and footer disclaimer live here)
- `web/lib/analytics.ts` — all analytics computations (port of export_analytics.py)
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

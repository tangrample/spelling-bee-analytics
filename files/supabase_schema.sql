-- Spelling Bee Analytics — Supabase Schema
-- Run this in the Supabase SQL Editor (supabase.com → your project → SQL Editor)
--
-- Phase 1: user_id is nullable (single-user, no auth yet)
-- Phase 2: user_id becomes NOT NULL and RLS policies are tightened

-- ── games ─────────────────────────────────────────────────────────────────────
CREATE TABLE games (
  id                  BIGSERIAL PRIMARY KEY,
  user_id             UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  puzzle_date         DATE NOT NULL,
  puzzle_letters      TEXT NOT NULL,
  center_letter       TEXT NOT NULL,
  score               INTEGER NOT NULL,
  max_possible_score  INTEGER,
  rank_achieved       TEXT,
  is_genius           BOOLEAN DEFAULT FALSE,
  is_queen_bee        BOOLEAN DEFAULT FALSE,
  is_gn4l             BOOLEAN DEFAULT FALSE,
  is_revealed         BOOLEAN DEFAULT FALSE,
  total_words_found   INTEGER DEFAULT 0,
  total_possible_words INTEGER,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, puzzle_date)
);

-- ── words_found ───────────────────────────────────────────────────────────────
CREATE TABLE words_found (
  id        BIGSERIAL PRIMARY KEY,
  game_id   BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  word      TEXT NOT NULL,
  points    INTEGER NOT NULL,
  is_pangram BOOLEAN DEFAULT FALSE,
  length    INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (game_id, word)
);

-- ── puzzle_answers ────────────────────────────────────────────────────────────
CREATE TABLE puzzle_answers (
  id        BIGSERIAL PRIMARY KEY,
  game_id   BIGINT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  word      TEXT NOT NULL,
  points    INTEGER NOT NULL,
  is_pangram BOOLEAN DEFAULT FALSE,
  length    INTEGER NOT NULL,
  UNIQUE (game_id, word)
);

-- ── words_missed (view) ───────────────────────────────────────────────────────
CREATE VIEW words_missed AS
  SELECT pa.*
  FROM puzzle_answers pa
  WHERE NOT EXISTS (
    SELECT 1 FROM words_found wf
    WHERE wf.game_id = pa.game_id AND wf.word = pa.word
  );

-- ── Row Level Security ────────────────────────────────────────────────────────
-- Phase 1: open access (single personal user, no auth)
-- Phase 2: replace these with user_id-scoped policies

ALTER TABLE games          ENABLE ROW LEVEL SECURITY;
ALTER TABLE words_found    ENABLE ROW LEVEL SECURITY;
ALTER TABLE puzzle_answers ENABLE ROW LEVEL SECURITY;

-- Allow full access via anon key (Phase 1 only — tighten in Phase 2)
CREATE POLICY "phase1_open" ON games          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "phase1_open" ON words_found    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "phase1_open" ON puzzle_answers FOR ALL USING (true) WITH CHECK (true);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX idx_games_puzzle_date    ON games (puzzle_date DESC);
CREATE INDEX idx_words_found_game_id  ON words_found (game_id);
CREATE INDEX idx_puzzle_answers_game  ON puzzle_answers (game_id);

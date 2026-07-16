-- Spelling Bee Analytics — word_definitions table
-- Run this in the Supabase SQL Editor (supabase.com → your project → SQL Editor)
--
-- Caches word definitions fetched from the free dictionaryapi.dev lookup, so the
-- dashboard doesn't need to hit an external API on every load. Backfilled once by
-- files/backfill_definitions.py, then kept up to date automatically — analytics.ts
-- fetches definitions for any newly-missed word that isn't cached yet and writes
-- the result back here.

CREATE TABLE word_definitions (
  word        TEXT PRIMARY KEY,
  definition  TEXT NOT NULL,
  source      TEXT DEFAULT 'dictionaryapi.dev',
  fetched_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE word_definitions ENABLE ROW LEVEL SECURITY;

-- Phase 1: open access, consistent with games/words_found/puzzle_answers (see supabase_schema.sql)
CREATE POLICY "phase1_open" ON word_definitions FOR ALL USING (true) WITH CHECK (true);

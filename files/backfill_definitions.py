#!/usr/bin/env python3
"""
One-off backfill: fetch definitions for every "study word" (missed >=1 time,
appeared >=2 times, matching the same filter used in web/lib/analytics.ts)
that isn't already cached in Supabase's word_definitions table, using the
free dictionaryapi.dev lookup. Safe to re-run — skips words already cached.

Run this once after creating the word_definitions table
(files/add_word_definitions_table.sql). Delete this script afterwards if you
like; analytics.ts handles ongoing new-word lookups itself going forward.

Requires: requests
Reads Supabase URL + key from web/.env.local
"""
import os
import re
import time
import requests
from collections import defaultdict

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "web", ".env.local")


def load_env(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def sb_get(url, key, table, params):
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    resp = requests.get(f"{url}/rest/v1/{table}", headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def sb_upsert(url, key, table, rows):
    if not rows:
        return
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(f"{url}/rest/v1/{table}", headers=headers, json=rows, timeout=30)
    resp.raise_for_status()


def fetch_all_paginated(url, key, table, select):
    rows, offset, page = [], 0, 1000
    while True:
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Range": f"{offset}-{offset + page - 1}",
        }
        resp = requests.get(f"{url}/rest/v1/{table}?select={select}", headers=headers, timeout=30)
        resp.raise_for_status()
        batch = resp.json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return rows


def lookup_definition(word, retries=3):
    """Returns (definition_or_None, reason). reason is only set on failure, e.g.
    'rate_limited', 'not_found', 'error:<status>', 'exception:<msg>'."""
    for attempt in range(retries):
        try:
            r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=8)
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None, f"exception:{e}"

        if r.status_code == 429:
            # Rate limited — back off and retry rather than recording a false "no entry"
            wait = int(r.headers.get("Retry-After", 2 ** (attempt + 2)))
            if attempt < retries - 1:
                time.sleep(wait)
                continue
            return None, "rate_limited"

        if r.status_code == 404:
            return None, "not_found"

        if r.status_code != 200:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None, f"error:{r.status_code}"

        data = r.json()
        for entry in data:
            for meaning in entry.get("meanings", []):
                for d in meaning.get("definitions", []):
                    text = d.get("definition")
                    if text:
                        return text.strip().rstrip("."), None
        return None, "no_definition_in_response"
    return None, "unknown"


def main():
    env = load_env(ENV_PATH)
    url = env["NEXT_PUBLIC_SUPABASE_URL"]
    # Service role key bypasses RLS for the upsert; falls back to anon (works too, since
    # word_definitions uses an open phase1 policy) if service key isn't present locally.
    key = env.get("SUPABASE_SERVICE_ROLE_KEY") or env["NEXT_PUBLIC_SUPABASE_ANON_KEY"]

    print("Fetching puzzle_answers and words_found from Supabase...")
    answers = fetch_all_paginated(url, key, "puzzle_answers", "game_id,word")
    found = fetch_all_paginated(url, key, "words_found", "game_id,word")
    found_set = {(r["game_id"], r["word"]) for r in found}

    stats = defaultdict(lambda: {"appearances": 0, "missed": 0})
    for a in answers:
        s = stats[a["word"]]
        s["appearances"] += 1
        if (a["game_id"], a["word"]) not in found_set:
            s["missed"] += 1

    study_words = sorted(w for w, s in stats.items() if s["appearances"] >= 2 and s["missed"] > 0)
    print(f"{len(study_words)} words qualify as study words.")

    cached = fetch_all_paginated(url, key, "word_definitions", "word")
    cached_words = {r["word"] for r in cached}
    todo = [w for w in study_words if w not in cached_words]
    print(f"{len(todo)} need a definition lookup ({len(cached_words)} already cached).")

    found_count, miss_count, retry_later = 0, 0, []
    batch = []
    for i, word in enumerate(todo, 1):
        definition, reason = lookup_definition(word)
        if definition:
            batch.append({"word": word, "definition": definition, "source": "dictionaryapi.dev"})
            found_count += 1
        elif reason == "not_found":
            miss_count += 1
            print(f"  no dictionary entry: {word}")
        else:
            # rate-limited / transient error — don't record a false negative, just retry later
            retry_later.append(word)
            print(f"  skipped (will retry): {word} [{reason}]")
        if len(batch) >= 25:
            sb_upsert(url, key, "word_definitions", batch)
            batch = []
        if i % 25 == 0:
            print(f"  ...{i}/{len(todo)}")
        time.sleep(0.4)  # be polite to the free API — avoids tripping its rate limit

    sb_upsert(url, key, "word_definitions", batch)

    # Second pass for anything that failed due to rate limiting/transient errors, after a cooldown
    if retry_later:
        print(f"\nCooling down 15s, then retrying {len(retry_later)} word(s) that hit transient errors...")
        time.sleep(15)
        batch = []
        for word in retry_later:
            definition, reason = lookup_definition(word)
            if definition:
                batch.append({"word": word, "definition": definition, "source": "dictionaryapi.dev"})
                found_count += 1
            elif reason == "not_found":
                miss_count += 1
                print(f"  no dictionary entry: {word}")
            else:
                miss_count += 1
                print(f"  still failing, giving up for now: {word} [{reason}]")
            time.sleep(0.6)
        sb_upsert(url, key, "word_definitions", batch)

    print(f"\nDone. {found_count} definitions cached, {miss_count} words had no dictionary entry or"
          f" kept failing (these will keep showing as '<length>-letter word' until you re-run the script).")


if __name__ == "__main__":
    main()

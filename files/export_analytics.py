#!/usr/bin/env python3
"""
Export Spelling Bee analytics to docs/data.json for the GitHub Pages dashboard.
Run automatically by bee_sync.sh after each sync.
"""
import sqlite3
import json
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'spelling_bee.db')
DOCS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), 'docs')
OUT_PATH = os.path.join(DOCS_DIR, 'data.json')

os.makedirs(DOCS_DIR, exist_ok=True)

DEFINITIONS = {
    'imam':       'Islamic prayer leader',
    'iota':       'a tiny amount',
    'annatto':    'orange food dye from seeds',
    'gigging':    'playing live music gigs',
    'illy':       'archaic: badly, poorly',
    'laic':       'of the laity; secular',
    'olio':       'a mixture or medley',
    'rani':       'an Indian queen',
    'boor':       'rude, unmannerly person',
    'nada':       'nothing',
    'acai':       'purple berry from Brazil',
    'chic':       'stylishly elegant',
    'ciao':       'Italian hello/goodbye',
    'grog':       'diluted alcoholic drink',
    'idyl':       'short poem of simple charm',
    'lieu':       'in place of; instead of',
    'loco':       'crazy (informal)',
    'magi':       'the Three Wise Men',
    'maim':       'to injure or disable',
    'mete':       'to distribute or allot',
    'moan':       'low sound of pain or grief',
    'naan':       'leavened South Asian flatbread',
    'nene':       "Hawaii's state bird",
    'okra':       'green pod vegetable',
    'oral':       'spoken; relating to the mouth',
    'orca':       'killer whale',
    'tapa':       'Spanish small dish',
    'alto':       'low female singing voice',
    'titan':      'person of great power/strength',
    'monomania':  'obsession with one idea',
    'acacia':     'thorny flowering tree',
    'pipeline':   'channel for conveying something',
    'laudably':   'in a praiseworthy manner',
    'ignoring':   'paying no attention to',
    'backcomb':   'comb hair towards the roots',
    'unceded':    'not formally surrendered',
    'titmice':    'plural of titmouse (small bird)',
    'titanic':    'of enormous size or strength',
    'ottoman':    'padded seat or footstool',
    'minicam':    'small portable camera',
    'lanolin':    'grease from sheep wool',
    'hamachi':    'Japanese yellowtail fish',
    'edamame':    'young soybeans in the pod',
    'digging':    'excavating or searching through',
    'academe':    'the academic world',
    'imagining':  'forming a mental image of',
    'gadding':    'moving from place to place',
    'ennui':      'listless boredom',
    'gamin':      'a street urchin',
    'guru':       'a spiritual or expert guide',
    'arrant':     'complete, utter (usually negative)',
    'airman':     'a pilot or air force member',
    'annal':      'a historical record by year',
    'aril':       'seed covering of some fruits',
    'clay':       'fine-grained earthy material',
    'dino':       'informal for dinosaur',
    'heath':      'open uncultivated land',
    'acne':       'skin condition with pimples',
    'amen':       'so be it (religious affirmation)',
    'anti':       'opposed to',
    'cane':       'a walking stick; sugar plant',
    'chai':       'spiced milk tea',
    'chia':       'plant with edible seeds',
}

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return 1

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # ── Summary stats ─────────────────────────────────────────────────────────
    row = cur.execute('''
        SELECT
            COUNT(*) total_games,
            ROUND(AVG(CAST(score AS FLOAT)/NULLIF(max_possible_score,0))*100, 1) avg_score_pct,
            ROUND((1 - AVG(CAST(total_words_found AS FLOAT)/NULLIF(total_possible_words,0)))*100, 1) word_miss_rate,
            SUM(is_genius) genius,
            SUM(is_queen_bee) qb,
            MIN(puzzle_date) first_date,
            MAX(puzzle_date) last_date
        FROM games
    ''').fetchone()

    games_with_answers = cur.execute(
        'SELECT COUNT(DISTINCT game_id) FROM puzzle_answers'
    ).fetchone()[0]

    pg = cur.execute('''
        SELECT COUNT(*) total,
            SUM(CASE WHEN wf.word IS NOT NULL THEN 1 ELSE 0 END) found
        FROM puzzle_answers pa
        LEFT JOIN words_found wf ON wf.game_id = pa.game_id AND wf.word = pa.word
        WHERE pa.is_pangram = 1
    ''').fetchone()

    summary = {
        'total_games':        row[0],
        'games_with_answers': games_with_answers,
        'avg_score_pct':      row[1],
        'word_miss_rate':     row[2],
        'genius_count':       row[3],
        'genius_rate':        round(row[3] / row[0] * 100, 1),
        'qb_count':           row[4],
        'first_date':         row[5],
        'last_date':          row[6],
        'pangram_total':      pg[0],
        'pangram_found':      pg[1],
        'pangram_missed':     pg[0] - pg[1],
        'pangram_pct':        round(pg[1] / pg[0] * 100, 1),
        'pangram_miss_pct':   round((pg[0] - pg[1]) / pg[0] * 100, 1),
    }

    # ── Monthly stats ─────────────────────────────────────────────────────────
    monthly = []
    for r in cur.execute('''
        SELECT strftime("%Y-%m", puzzle_date) month,
               COUNT(*) games,
               ROUND(AVG(CAST(score AS FLOAT)/NULLIF(max_possible_score,0))*100, 1) score_pct,
               ROUND(AVG(CAST(total_words_found AS FLOAT)/NULLIF(total_possible_words,0))*100, 1) words_pct,
               SUM(is_genius) genius, SUM(is_queen_bee) qb
        FROM games GROUP BY month ORDER BY month
    '''):
        monthly.append({
            'month': r[0], 'games': r[1],
            'score_pct': r[2], 'words_pct': r[3],
            'genius': r[4], 'qb': r[5],
        })

    # ── Miss rate by length (group 8+) ────────────────────────────────────────
    miss_by_length = []
    for r in cur.execute('''
        SELECT
            CASE WHEN pa.length >= 8 THEN 8 ELSE pa.length END as len_group,
            COUNT(*) total,
            SUM(CASE WHEN wf.word IS NULL THEN 1 ELSE 0 END) missed
        FROM puzzle_answers pa
        LEFT JOIN words_found wf ON wf.game_id = pa.game_id AND wf.word = pa.word
        GROUP BY len_group ORDER BY len_group
    '''):
        total, missed = r[1], r[2]
        miss_by_length.append({
            'length':   r[0],
            'label':    '8+ letter' if r[0] >= 8 else f'{r[0]}-letter',
            'total':    total,
            'missed':   missed,
            'miss_pct': round(missed / total * 100, 1) if total else 0,
        })

    # ── Study words (weighted: miss_rate × length × appearances) ─────────────
    study_words = []
    for r in cur.execute('''
        SELECT pa.word,
               COUNT(*) appearances,
               SUM(CASE WHEN wf.word IS NULL THEN 1 ELSE 0 END) missed,
               ROUND(SUM(CASE WHEN wf.word IS NULL THEN 1.0 ELSE 0 END)/COUNT(*)*100, 1) miss_pct,
               MAX(pa.length) word_len,
               MAX(pa.is_pangram) is_pangram,
               ROUND(
                   (SUM(CASE WHEN wf.word IS NULL THEN 1.0 ELSE 0 END)/COUNT(*)) *
                   (MAX(pa.length) * 1.0 / 4) *
                   CASE WHEN MAX(pa.is_pangram)=1 THEN 3.0 ELSE 1.0 END *
                   COUNT(*) / 3.0
               , 2) weight
        FROM puzzle_answers pa
        LEFT JOIN words_found wf ON wf.game_id = pa.game_id AND wf.word = pa.word
        GROUP BY pa.word
        HAVING appearances >= 2 AND missed > 0
        ORDER BY weight DESC, miss_pct DESC
        LIMIT 100
    '''):
        study_words.append({
            'word':        r[0],
            'appearances': r[1],
            'missed':      r[2],
            'miss_pct':    r[3],
            'length':      r[4],
            'is_pangram':  bool(r[5]),
            'weight':      r[6],
            'definition':  DEFINITIONS.get(r[0], ''),
        })

    # ── Missed pangrams ────────────────────────────────────────────────────────
    missed_pangrams = []
    for r in cur.execute('''
        SELECT pa.word, g.puzzle_date, pa.points, pa.length
        FROM puzzle_answers pa
        JOIN games g ON g.id = pa.game_id
        LEFT JOIN words_found wf ON wf.game_id = pa.game_id AND wf.word = pa.word
        WHERE pa.is_pangram = 1 AND wf.word IS NULL
        ORDER BY g.puzzle_date DESC
    '''):
        missed_pangrams.append({
            'word': r[0], 'date': r[1], 'points': r[2], 'length': r[3]
        })

    con.close()

    data = {
        'generated_at':   datetime.now().isoformat(),
        'summary':        summary,
        'monthly':        monthly,
        'miss_by_length': miss_by_length,
        'study_words':    study_words,
        'missed_pangrams': missed_pangrams,
    }

    with open(OUT_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"📊 Exported analytics → docs/data.json")
    print(f"   {len(study_words)} study words · {len(missed_pangrams)} missed pangrams")
    return 0

if __name__ == '__main__':
    exit(main())

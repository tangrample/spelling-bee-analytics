/**
 * NYT Spelling Bee — Archive Puzzle Extractor
 *
 * USE THIS when visiting an individual archive puzzle (not the main page).
 * It saves ONLY the puzzle metadata for that one date, appending it to a
 * running "archive_metadata.json" accumulator file. After you've visited
 * all missing dates, run: python3 archive_merge.py
 *
 * WORKFLOW:
 *   1. Go to the Spelling Bee archive page and click a past date
 *   2. Wait for the puzzle to fully load (hive visible)
 *   3. Open DevTools Console (F12 → Console tab)
 *   4. Paste this script and press Enter
 *   5. It downloads a small JSON snippet for that date
 *   6. Repeat for each missing date
 *   7. Run: python3 archive_merge.py  (merges everything + updates DB)
 */

(function () {
  // ── Find puzzle metadata ────────────────────────────────────────────────

  let puzzleData = null;

  // Method 1: window.gameData
  if (window.gameData) {
    const src = window.gameData.today || window.gameData;
    if (src && src.centerLetter) puzzleData = { ...src, _source: 'window.gameData' };
  }

  // Method 2: React fiber tree
  if (!puzzleData) {
    function isPuzzle(obj) {
      return obj && typeof obj === 'object' &&
        ('centerLetter' in obj || 'center_letter' in obj) &&
        ('outerLetters' in obj || 'letters' in obj) &&
        ('answers' in obj || 'validLetters' in obj);
    }
    function search(obj, depth, seen) {
      if (depth > 20 || !obj || typeof obj !== 'object' || seen.has(obj)) return null;
      seen.add(obj);
      if (isPuzzle(obj)) return obj;
      for (const k of Object.keys(obj)) {
        try { const r = search(obj[k], depth + 1, seen); if (r) return r; } catch (_) {}
      }
      return null;
    }
    for (const el of [document.getElementById('app'), document.body].filter(Boolean)) {
      for (const k of Object.keys(el)) {
        if (k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')) {
          const found = search(el[k], 0, new WeakSet());
          if (found) { puzzleData = { ...found, _source: 'react_fiber' }; break; }
        }
      }
      if (puzzleData) break;
    }
  }

  // Method 3: Embedded <script> JSON
  if (!puzzleData) {
    for (const s of document.querySelectorAll('script')) {
      const txt = s.textContent || '';
      const m = txt.match(/"centerLetter"\s*:\s*"([A-Z])"/i);
      if (m) {
        const start = txt.lastIndexOf('{', txt.indexOf('"centerLetter"'));
        if (start !== -1) {
          try {
            let d = 0, end = start;
            for (let i = start; i < txt.length; i++) {
              if (txt[i] === '{') d++;
              else if (txt[i] === '}' && --d === 0) { end = i; break; }
            }
            const candidate = JSON.parse(txt.slice(start, end + 1));
            if (candidate.centerLetter) { puzzleData = { ...candidate, _source: 'script_tag' }; break; }
          } catch (_) {}
        }
      }
    }
  }

  if (!puzzleData) {
    alert('❌ Could not find puzzle data.\n\nMake sure:\n1. You clicked into a specific archive puzzle (hive is visible)\n2. The puzzle has fully loaded\n3. Try refreshing and waiting a few seconds');
    return;
  }

  // ── Extract key fields ──────────────────────────────────────────────────

  const date = puzzleData.printDate ||
               puzzleData.print_date ||
               new Date().toISOString().split('T')[0];

  const snippet = {
    date:          date,
    puzzle_id:     String(puzzleData.id || puzzleData.puzzleId || ''),
    center_letter: (puzzleData.centerLetter || puzzleData.center_letter || '').toUpperCase(),
    outer_letters: (puzzleData.outerLetters || puzzleData.outer_letters || []).map(l => l.toUpperCase()),
    all_words:     puzzleData.answers || puzzleData.validWords || [],
    pangrams:      puzzleData.pangrams || [],
    _source:       puzzleData._source,
  };

  console.log(`✓ Captured puzzle for ${snippet.date}: center=${snippet.center_letter}, ${snippet.all_words.length} words, ${snippet.pangrams.length} pangrams`);

  // ── Download ────────────────────────────────────────────────────────────

  const blob = new Blob([JSON.stringify(snippet, null, 2)], { type: 'application/json' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'bee_archive_' + date + '.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log(`✅ Downloaded: bee_archive_${date}.json  — move to your project folder, then continue with the next date.`);
})();

/**
 * NYT Spelling Bee Data Extractor — v3 (Multi-method)
 *
 * USAGE:
 *   1. Go to https://www.nytimes.com/puzzles/spelling-bee
 *   2. Wait for the puzzle to fully load (hive should be visible)
 *   3. Open DevTools: F12 (Windows/Linux) or Cmd+Option+I (Mac)
 *   4. Click the "Console" tab
 *   5. Paste this entire script and press Enter
 *   6. A JSON file will download — save it as spelling_bee_raw.json
 *
 * WHY THIS VERSION: NYT removed window.gameData from the global scope.
 * This script tries 4 methods to recover puzzle metadata.
 */

(function () {
  console.log('🐝 Spelling Bee Extractor v3 — starting...');
  const data = {};

  // ─── STEP 1: Game state from localStorage ────────────────────────────────
  // This stores your personal answers, rank, etc.
  console.log('\n[1/4] Scanning localStorage...');
  const lsKeys = [];
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (
      key.includes('spelling_bee') ||
      key.includes('spelling-bee') ||
      key.includes('sb-') ||
      key.includes('games-state')
    ) {
      try {
        data[key] = JSON.parse(localStorage.getItem(key));
        lsKeys.push(key);
      } catch (e) {
        data[key] = localStorage.getItem(key);
        lsKeys.push(key + ' (raw string)');
      }
    }
  }
  console.log(lsKeys.length > 0
    ? '  ✓ Found localStorage keys: ' + lsKeys.join(', ')
    : '  ✗ No Spelling Bee keys in localStorage');

  // ─── STEP 2: window.gameData (classic — may no longer work) ──────────────
  console.log('\n[2/4] Checking window.gameData...');
  if (typeof window.gameData !== 'undefined') {
    data['_window_gameData'] = window.gameData;
    console.log('  ✓ Found window.gameData');
  } else {
    console.log('  ✗ window.gameData not found — trying alternatives...');

    // ─── STEP 3: React fiber tree search ───────────────────────────────────
    // NYT's React app holds puzzle state in component fiber props/state.
    // We walk the fiber tree looking for objects that have centerLetter +
    // outerLetters + answers, which is the puzzle shape.
    console.log('\n[3/4] Searching React fiber tree for puzzle data...');

    function isPuzzleShape(obj) {
      if (!obj || typeof obj !== 'object') return false;
      return (
        ('centerLetter' in obj || 'center_letter' in obj) &&
        ('outerLetters' in obj || 'outer_letters' in obj || 'letters' in obj) &&
        ('answers' in obj || 'validLetters' in obj)
      );
    }

    function deepSearch(obj, maxDepth, depth, seen) {
      if (depth > maxDepth || !obj || typeof obj !== 'object') return null;
      if (seen.has(obj)) return null;
      seen.add(obj);
      if (isPuzzleShape(obj)) return obj;
      for (const key of Object.keys(obj)) {
        try {
          const result = deepSearch(obj[key], maxDepth, depth + 1, seen);
          if (result) return result;
        } catch (_) {}
      }
      return null;
    }

    function getFiberRoot(el) {
      if (!el) return null;
      for (const key of Object.keys(el)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
          return el[key];
        }
      }
      return null;
    }

    let puzzleFromFiber = null;
    const candidateEls = [
      document.getElementById('app'),
      document.querySelector('[data-testid="spelling-bee-game"]'),
      document.querySelector('.pz-game-screen'),
      document.querySelector('#spelling-bee-container'),
      document.body,
    ].filter(Boolean);

    for (const el of candidateEls) {
      const fiber = getFiberRoot(el);
      if (!fiber) continue;
      const seen = new WeakSet();
      const found = deepSearch(fiber, 25, 0, seen);
      if (found) {
        puzzleFromFiber = found;
        console.log('  ✓ Found puzzle data in React fiber tree');
        break;
      }
    }

    if (puzzleFromFiber) {
      // Wrap it in the same shape parse_nyt_data.py expects
      data['_window_gameData'] = {
        today: puzzleFromFiber,
        _source: 'react_fiber',
      };
    } else {
      console.log('  ✗ React fiber search came up empty');

      // ─── STEP 4: Embedded <script> JSON search ────────────────────────────
      // Many NYT pages embed initial state as JSON inside a <script> tag.
      console.log('\n[4/4] Searching for embedded JSON in page <script> tags...');
      const scripts = document.querySelectorAll('script');
      let foundFromScript = false;
      for (const s of scripts) {
        const txt = s.textContent || '';
        // Look for the characteristic shape of the puzzle JSON
        const match = txt.match(/"centerLetter"\s*:\s*"([A-Z])"/i);
        if (match) {
          // Try to extract surrounding JSON object
          const startIdx = txt.lastIndexOf('{', txt.indexOf('"centerLetter"'));
          if (startIdx !== -1) {
            try {
              // Find the matching closing brace
              let depth = 0;
              let endIdx = startIdx;
              for (let i = startIdx; i < txt.length; i++) {
                if (txt[i] === '{') depth++;
                else if (txt[i] === '}') {
                  depth--;
                  if (depth === 0) { endIdx = i; break; }
                }
              }
              const candidate = JSON.parse(txt.slice(startIdx, endIdx + 1));
              if (isPuzzleShape(candidate)) {
                data['_window_gameData'] = {
                  today: candidate,
                  _source: 'embedded_script',
                };
                console.log('  ✓ Found puzzle data in embedded <script> JSON');
                foundFromScript = true;
                break;
              }
            } catch (_) {}
          }
        }
      }
      if (!foundFromScript) {
        console.log('  ✗ No embedded puzzle JSON found');
        console.warn(
          '\n⚠️  Could NOT find puzzle metadata (letters, word list, pangrams).' +
          '\n   Your game history (words you found, rank) IS captured.' +
          '\n   To get full puzzle data, try running this script right after' +
          '\n   the page loads and before playing — or see EXTRACT_DATA.md for' +
          '\n   the fetch-intercept method.'
        );
      }
    }
  }

  // ─── SUMMARY ─────────────────────────────────────────────────────────────
  const hasPuzzleData = '_window_gameData' in data;
  const hasGameState  = Object.keys(data).some(k => k.includes('games-state') || k.includes('spelling_bee'));
  console.log('\n══════════════════════════════════════');
  console.log('📊 Extraction summary:');
  console.log('  Game state (your answers):  ' + (hasGameState  ? '✓' : '✗'));
  console.log('  Puzzle metadata (letters):  ' + (hasPuzzleData ? '✓' : '✗'));
  console.log('  Source: ' + (data['_window_gameData']?._source || (hasPuzzleData ? 'window.gameData' : 'none')));
  console.log('══════════════════════════════════════\n');

  if (!hasGameState && !hasPuzzleData) {
    alert('❌ No data found at all.\n\nMake sure:\n1. You are on the NYT Spelling Bee page\n2. The puzzle has fully loaded\n3. You are logged in to your NYT account');
    return;
  }

  // ─── DOWNLOAD ────────────────────────────────────────────────────────────
  const json    = JSON.stringify(data, null, 2);
  const blob    = new Blob([json], { type: 'application/json' });
  const url     = URL.createObjectURL(blob);
  const a       = document.createElement('a');
  const today   = new Date().toISOString().split('T')[0];
  a.href        = url;
  a.download    = 'spelling_bee_raw_' + today + '.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log('✅ Download started! Save the file as spelling_bee_raw.json');
  console.log('   Then run: python3 parse_nyt_data.py');
})();

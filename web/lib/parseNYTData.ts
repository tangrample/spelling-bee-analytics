// Port of parse_nyt_data.py + process_data.py
// Used server-side in /api/sync to process raw bookmarklet JSON

export type ParsedWord = {
  word: string
  points: number
  is_pangram: boolean
  length: number
}

export type ParsedGame = {
  gameRecord: {
    puzzle_date: string
    puzzle_letters: string
    center_letter: string
    score: number
    max_possible_score: number | null
    rank_achieved: string
    is_genius: boolean
    is_queen_bee: boolean
    is_gn4l: boolean
    is_revealed: boolean
    total_words_found: number
    total_possible_words: number | null
  }
  wordsFound: ParsedWord[]
  puzzleAnswers: ParsedWord[]  // empty if not yet revealed
}

// ── Scoring ───────────────────────────────────────────────────────────────────

function wordPoints(word: string, pangram: boolean): number {
  return (word.length === 4 ? 1 : word.length) + (pangram ? 7 : 0)
}

function checkPangram(word: string, allLetters: string): boolean {
  const wl = new Set(word.toLowerCase())
  return [...allLetters.toLowerCase()].every(l => wl.has(l))
}

function rankFromPct(pct: number): string {
  if (pct >= 100) return 'Queen Bee'
  if (pct >= 70)  return 'Genius'
  if (pct >= 50)  return 'Amazing'
  if (pct >= 40)  return 'Great'
  if (pct >= 25)  return 'Nice'
  if (pct >= 15)  return 'Solid'
  if (pct >= 8)   return 'Good'
  if (pct >= 5)   return 'Moving Up'
  if (pct >= 2)   return 'Good Start'
  return 'Beginner'
}

// ── Main parser ───────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function parseNYTData(rawData: Record<string, any>): ParsedGame[] {
  // Find the games-state key (prefer authenticated over ANON)
  let gamesStateKey: string | null = null
  let anonKey: string | null = null

  for (const key of Object.keys(rawData)) {
    if (key.includes('games-state-spelling_bee')) {
      if (key.endsWith('/ANON')) {
        anonKey = key
      } else {
        gamesStateKey = key
        break
      }
    }
  }
  if (!gamesStateKey) gamesStateKey = anonKey
  if (!gamesStateKey) return []

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const gameStates: any[] = rawData[gamesStateKey]?.states ?? []
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const windowData: any = rawData['_window_gameData'] ?? {}

  // Build puzzle metadata index: puzzleId → info
  const puzzlesInfo: Record<string, {
    date: string; letters: string; centerLetter: string
    allWords: string[]; pangrams: string[]
  }> = {}

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function indexPuzzle(d: any) {
    if (!d?.printDate) return
    const id = String(d.id ?? '')
    if (!id) return
    puzzlesInfo[id] = {
      date:         d.printDate,
      letters:      (d.outerLetters ?? []).join(''),
      centerLetter: d.centerLetter ?? '',
      allWords:     d.answers ?? [],
      pangrams:     d.pangrams ?? [],
    }
  }

  const past = windowData.pastPuzzles ?? {}
  if (Object.keys(past).length > 0) {
    indexPuzzle(past.today)
    indexPuzzle(past.yesterday)
    for (const p of (past.thisWeek ?? [])) indexPuzzle(p)
    for (const p of (past.lastWeek ?? [])) indexPuzzle(p)
  } else {
    indexPuzzle(windowData.today)
    indexPuzzle(windowData.yesterday)
  }

  const games: ParsedGame[] = []

  for (const state of gameStates) {
    const puzzleId   = String(state.puzzleId ?? '')
    const gameData   = state.data ?? {}
    const foundRaw   = (gameData.answers ?? []) as string[]
    const isRevealed = Boolean(gameData.isRevealed ?? false)

    if (foundRaw.length === 0) continue
    const info = puzzlesInfo[puzzleId]
    if (!info) continue

    const allLetters = info.letters + info.centerLetter

    const wordsFound: ParsedWord[] = foundRaw.map(w => {
      const pan = checkPangram(w, allLetters)
      return { word: w.toLowerCase(), points: wordPoints(w, pan), is_pangram: pan, length: w.length }
    })

    const puzzleAnswers: ParsedWord[] = info.allWords.map(w => {
      const pan = checkPangram(w, allLetters)
      return { word: w.toLowerCase(), points: wordPoints(w, pan), is_pangram: pan, length: w.length }
    })

    const score    = wordsFound.reduce((s, w) => s + w.points, 0)
    const maxScore = puzzleAnswers.reduce((s, w) => s + w.points, 0)
    const pct      = maxScore > 0 ? score / maxScore * 100 : 0

    const points5Plus = wordsFound.filter(w => w.length >= 5).reduce((s, w) => s + w.points, 0)
    const isGn4l      = maxScore > 0 && points5Plus >= maxScore * 0.7

    games.push({
      gameRecord: {
        puzzle_date:          info.date,
        puzzle_letters:       allLetters.toUpperCase(),
        center_letter:        info.centerLetter.toUpperCase(),
        score,
        max_possible_score:   maxScore || null,
        rank_achieved:        (gameData.rank as string) || rankFromPct(pct),
        is_genius:            pct >= 70,
        is_queen_bee:         foundRaw.length === info.allWords.length && info.allWords.length > 0,
        is_gn4l:              isGn4l,
        is_revealed:          isRevealed,
        total_words_found:    foundRaw.length,
        total_possible_words: info.allWords.length || null,
      },
      wordsFound,
      puzzleAnswers: isRevealed ? puzzleAnswers : [],
    })
  }

  return games
}

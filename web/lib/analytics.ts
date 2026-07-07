import { supabase } from './supabase'

// Fetch all rows from a table, paginating past Supabase's 1000-row default limit
async function fetchAll<T>(queryFn: () => any): Promise<T[]> {
  const PAGE = 1000
  let offset = 0
  const results: T[] = []
  while (true) {
    const { data, error } = await queryFn().range(offset, offset + PAGE - 1)
    if (error) throw new Error(error.message)
    results.push(...(data as T[]))
    if ((data as T[]).length < PAGE) break
    offset += PAGE
  }
  return results
}

// ── Types ────────────────────────────────────────────────────────────────────

type Game = {
  id: number
  puzzle_date: string
  score: number
  max_possible_score: number | null
  is_genius: boolean
  is_queen_bee: boolean
  is_gn4l: boolean
  is_revealed: boolean
  total_words_found: number
  total_possible_words: number | null
}

type WordFound = {
  game_id: number
  word: string
  is_pangram: boolean
  length: number
}

type PuzzleAnswer = {
  game_id: number
  word: string
  points: number
  is_pangram: boolean
  length: number
}

export type WordDefinitionRow = {
  word: string
  definition: string
}

export type StudyWord = {
  word: string
  appearances: number
  missed: number
  miss_pct: number
  length: number
  is_pangram: boolean
  weight: number
  last_missed: string | null
  definition: string
}

export type MissedPangram = {
  word: string
  date: string
  points: number
  length: number
}

export type MonthStat = {
  month: string
  games: number
  score_pct: number
  words_pct: number
  genius: number
  qb: number
}

export type WeekStat = {
  week: string // ISO date of the Monday that starts the week
  games: number
  score_pct: number
  words_pct: number
  genius: number
  qb: number
}

export type LengthStat = {
  length: number
  label: string
  total: number
  missed: number
  miss_pct: number
}

export type MissByLength = {
  last7: LengthStat[]
  last30: LengthStat[]
  all: LengthStat[]
}

export type Summary = {
  total_games: number
  games_with_answers: number
  avg_score_pct: number
  word_miss_rate: number
  genius_count: number
  genius_rate: number
  qb_count: number
  first_date: string
  last_date: string
  pangram_total: number
  pangram_found: number
  pangram_missed: number
  pangram_pct: number
  pangram_miss_pct: number
}

export type Recent = {
  games: number
  avg_score_pct: number
  genius_count: number
  word_miss_rate: number
  pangram_found: number
  pangram_total: number
}

export type AnalyticsData = {
  generated_at: string
  summary: Summary
  recent: Recent
  monthly: MonthStat[]
  weekly: WeekStat[]
  miss_by_length: MissByLength
  study_words: StudyWord[]
  missed_pangrams: MissedPangram[]
}

// ── Word definitions ──────────────────────────────────────────────────────────

const DEFINITIONS: Record<string, string> = {
  imam:       'Islamic prayer leader',
  iota:       'a tiny amount',
  annatto:    'orange food dye from seeds',
  gigging:    'playing live music gigs',
  illy:       'archaic: badly, poorly',
  laic:       'of the laity; secular',
  olio:       'a mixture or medley',
  rani:       'an Indian queen',
  boor:       'rude, unmannerly person',
  nada:       'nothing',
  acai:       'purple berry from Brazil',
  chic:       'stylishly elegant',
  ciao:       'Italian hello/goodbye',
  grog:       'diluted alcoholic drink',
  idyl:       'short poem of simple charm',
  lieu:       'in place of; instead of',
  loco:       'crazy (informal)',
  magi:       'the Three Wise Men',
  maim:       'to injure or disable',
  mete:       'to distribute or allot',
  moan:       'low sound of pain or grief',
  naan:       'leavened South Asian flatbread',
  nene:       "Hawaii's state bird",
  okra:       'green pod vegetable',
  oral:       'spoken; relating to the mouth',
  orca:       'killer whale',
  tapa:       'Spanish small dish',
  alto:       'low female singing voice',
  titan:      'person of great power/strength',
  monomania:  'obsession with one idea',
  acacia:     'thorny flowering tree',
  pipeline:   'channel for conveying something',
  laudably:   'in a praiseworthy manner',
  ignoring:   'paying no attention to',
  backcomb:   'comb hair towards the roots',
  unceded:    'not formally surrendered',
  titmice:    'plural of titmouse (small bird)',
  titanic:    'of enormous size or strength',
  ottoman:    'padded seat or footstool',
  minicam:    'small portable camera',
  lanolin:    'grease from sheep wool',
  hamachi:    'Japanese yellowtail fish',
  edamame:    'young soybeans in the pod',
  digging:    'excavating or searching through',
  academe:    'the academic world',
  imagining:  'forming a mental image of',
  gadding:    'moving from place to place',
  ennui:      'listless boredom',
  gamin:      'a street urchin',
  guru:       'a spiritual or expert guide',
  arrant:     'complete, utter (usually negative)',
  airman:     'a pilot or air force member',
  annal:      'a historical record by year',
  aril:       'seed covering of some fruits',
  clay:       'fine-grained earthy material',
  dino:       'informal for dinosaur',
  heath:      'open uncultivated land',
  acne:       'skin condition with pimples',
  amen:       'so be it (religious affirmation)',
  anti:       'opposed to',
  cane:       'a walking stick; sugar plant',
  chai:       'spiced milk tea',
  chia:       'plant with edible seeds',
  // Manual overrides: dictionaryapi.dev's Wiktionary data lists a low-quality
  // or irrelevant sense first for these, and the general quality filter below
  // (added after noticing this) still can't fully replace human judgment —
  // "anal" has a legitimate but obscure "reptile scale" noun sense that beats
  // the length filter, and these entries are already cached in Supabase with
  // the bad values from before the filter existed, so an override here is the
  // most direct fix (hardcoded entries always take priority over the cache).
  anal:       'obsessively neat and precise; also, relating to the anus',
  adorn:      'to decorate or make more beautiful',
}

// Definitions this short/generic are almost always a word restating itself
// (e.g. "Adornment" for "adorn") rather than an actual definition, and are
// filtered out wherever raw dictionary API results are considered.
function isLowQualityDefinition(def: string): boolean {
  const trimmed = def.trim()
  if (trimmed.length < 15) return true
  // Light denylist for explicit/vulgar senses — this app surfaces definitions
  // for casual vocab study, not an unabridged dictionary, so skip past these
  // in favor of any other available sense of the word.
  if (/\b(sex|sexual|genitals?|masturbat\w*)\b/i.test(trimmed)) return true
  return false
}

// Cache-miss lookup against the free dictionaryapi.dev API for words not covered
// above and not yet in the word_definitions Supabase cache. Bounded + short timeout
// so a slow/unreachable API can't stall the dashboard.
async function lookupDictionaryApiDev(word: string): Promise<string | null> {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(`https://api.dictionaryapi.dev/api/v2/entries/en/${word}`, {
      signal: controller.signal,
    })
    clearTimeout(timeout)
    if (!res.ok) return null
    const data = await res.json()
    // Wiktionary doesn't order senses by "most useful" — a rare noun sense or
    // a bare word-restating-itself entry can easily land first (e.g. "anal"'s
    // "reptile scale" sense beats its far more common adjective senses; "adorn"'s
    // noun sense is literally just "Adornment"). Scan every definition across
    // every meaning and take the first one that clears the quality bar, only
    // falling back to whatever came first if nothing does (so a word where
    // every sense happens to be short doesn't lose coverage entirely).
    let fallback: string | null = null
    for (const entry of data) {
      for (const meaning of entry.meanings ?? []) {
        for (const def of meaning.definitions ?? []) {
          if (!def.definition) continue
          const cleaned = String(def.definition).trim().replace(/\.$/, '')
          if (!fallback) fallback = cleaned
          if (!isLowQualityDefinition(cleaned)) return cleaned
        }
      }
    }
    return fallback
  } catch {
    return null
  }
}

// Fallback lookup against Datamuse's word-definitions endpoint (WordNet-backed).
// dictionaryapi.dev is Wiktionary-backed and misses a fair number of regularly
// formed but less common derivations (e.g. "hateable", "healable" — valid
// -able adjectives that just don't have their own Wiktionary entry). Datamuse
// has broader WordNet coverage for exactly this kind of word, so it's tried
// second rather than first — dictionaryapi.dev's definitions tend to read more
// naturally, so it stays the preferred source when it has an entry at all.
async function lookupDatamuse(word: string): Promise<string | null> {
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 3000)
    const res = await fetch(
      // max=5 (not 1) so a same-spelling exact match further down the
      // ranked results still gets found — see exact-match check below.
      `https://api.datamuse.com/words?sp=${encodeURIComponent(word)}&md=d&max=5`,
      { signal: controller.signal }
    )
    clearTimeout(timeout)
    if (!res.ok) return null
    const data = await res.json()
    // IMPORTANT: `sp=` is a fuzzy "spelled like" query, not an exact lookup —
    // Datamuse will happily return the definition for a *different* word if
    // there's no exact match (e.g. querying "anagramming" returns
    // "diagramming"; querying "idylically" returns "idyllically"). Silently
    // attaching a wrong word's definition would be worse than the generic
    // "N-letter word" fallback, so only accept a result whose word matches
    // exactly (case-insensitive).
    const match = (data as { word: string; defs?: string[] }[]).find(
      d => d.word.toLowerCase() === word.toLowerCase()
    )
    const defs = match?.defs
    if (!defs || defs.length === 0) return null
    // Datamuse formats each entry as "pos\tdefinition text", e.g.
    // "adj\tCapable of being healed." — strip the part-of-speech tag, and
    // apply the same low-quality filter as the dictionaryapi.dev lookup
    // (Datamuse can list multiple senses too, in no particular quality order).
    let fallback: string | null = null
    for (const d of defs) {
      const cleaned = d.split('\t').slice(1).join('\t').trim().replace(/\.$/, '')
      if (!cleaned) continue
      if (!fallback) fallback = cleaned
      if (!isLowQualityDefinition(cleaned)) return cleaned
    }
    return fallback
  } catch {
    return null
  }
}

async function lookupDictionaryDefinition(word: string): Promise<string | null> {
  return (await lookupDictionaryApiDev(word)) ?? (await lookupDatamuse(word))
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function round(n: number, decimals: number): number {
  const factor = Math.pow(10, decimals)
  return Math.round(n * factor) / factor
}

function avg(nums: number[]): number {
  if (nums.length === 0) return 0
  return nums.reduce((a, b) => a + b, 0) / nums.length
}

// Monday (ISO) of the calendar week containing this date, as YYYY-MM-DD
function weekStart(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00')
  const day = d.getDay() // 0 = Sun ... 6 = Sat
  const diff = (day === 0 ? -6 : 1) - day
  d.setDate(d.getDate() + diff)
  return d.toISOString().slice(0, 10)
}

// ── Main analytics function ───────────────────────────────────────────────────

export async function getAnalytics(): Promise<AnalyticsData> {
  // Fetch all data (paginated to bypass 1000-row default limit)
  const [games, wordsFound, puzzleAnswers, cachedDefinitions] = await Promise.all([
    fetchAll<Game>(() => supabase.from('games').select('*').order('puzzle_date', { ascending: true })),
    fetchAll<WordFound>(() => supabase.from('words_found').select('game_id, word, is_pangram, length')),
    fetchAll<PuzzleAnswer>(() => supabase.from('puzzle_answers').select('game_id, word, points, is_pangram, length')),
    fetchAll<WordDefinitionRow>(() => supabase.from('word_definitions').select('word, definition')),
  ])
  const dbDefinitions = new Map(cachedDefinitions.map(d => [d.word, d.definition]))

  // Build lookup: game_id → set of found words
  const foundByGame = new Map<number, Set<string>>()
  for (const wf of wordsFound) {
    if (!foundByGame.has(wf.game_id)) foundByGame.set(wf.game_id, new Set())
    foundByGame.get(wf.game_id)!.add(wf.word)
  }

  // Build lookup: game_id → game
  const gameById = new Map<number, Game>()
  for (const g of games) gameById.set(g.id, g)

  // ── Summary ───────────────────────────────────────────────────────────────
  const totalGames = games.length
  const gamesWithScore = games.filter(g => g.max_possible_score && g.max_possible_score > 0)
  const avgScorePct = round(avg(gamesWithScore.map(g => g.score / g.max_possible_score! * 100)), 1)
  const gamesWithWords = games.filter(g => g.total_possible_words && g.total_possible_words > 0)
  const wordMissRate = round(avg(gamesWithWords.map(g => (1 - g.total_words_found / g.total_possible_words!) * 100)), 1)
  const geniusCount = games.filter(g => g.is_genius).length
  const qbCount = games.filter(g => g.is_queen_bee).length

  const gamesWithAnswersSet = new Set(puzzleAnswers.map(pa => pa.game_id))
  const gamesWithAnswers = gamesWithAnswersSet.size

  const allPangrams = puzzleAnswers.filter(pa => pa.is_pangram)
  const panggramTotal = allPangrams.length
  const pangramFound = allPangrams.filter(pa => foundByGame.get(pa.game_id)?.has(pa.word)).length

  const summary: Summary = {
    total_games:        totalGames,
    games_with_answers: gamesWithAnswers,
    avg_score_pct:      avgScorePct,
    word_miss_rate:     wordMissRate,
    genius_count:       geniusCount,
    genius_rate:        round(geniusCount / totalGames * 100, 1),
    qb_count:           qbCount,
    first_date:         games[0]?.puzzle_date ?? '',
    last_date:          games[games.length - 1]?.puzzle_date ?? '',
    pangram_total:      panggramTotal,
    pangram_found:      pangramFound,
    pangram_missed:     panggramTotal - pangramFound,
    pangram_pct:        panggramTotal > 0 ? round(pangramFound / panggramTotal * 100, 1) : 0,
    pangram_miss_pct:   panggramTotal > 0 ? round((panggramTotal - pangramFound) / panggramTotal * 100, 1) : 0,
  }

  // ── Recent (last 7 games) ─────────────────────────────────────────────────
  const recentGames = games.slice(-7)
  const recentIds = new Set(recentGames.map(g => g.id))
  const recentAnswers = puzzleAnswers.filter(pa => recentIds.has(pa.game_id))
  const recentPangrams = recentAnswers.filter(pa => pa.is_pangram)

  const recGamesWithScore = recentGames.filter(g => g.max_possible_score && g.max_possible_score > 0)
  const recAvgScorePct = round(avg(recGamesWithScore.map(g => g.score / g.max_possible_score! * 100)), 1)

  const recTotalWords = recentAnswers.length
  const recMissedWords = recentAnswers.filter(pa => !foundByGame.get(pa.game_id)?.has(pa.word)).length
  const recWordMissRate = recTotalWords > 0 ? round(recMissedWords / recTotalWords * 100, 1) : 0

  const recPangramFound = recentPangrams.filter(pa => foundByGame.get(pa.game_id)?.has(pa.word)).length

  const recent: Recent = {
    games:          recentGames.length,
    avg_score_pct:  recAvgScorePct,
    genius_count:   recentGames.filter(g => g.is_genius).length,
    word_miss_rate: recWordMissRate,
    pangram_found:  recPangramFound,
    pangram_total:  recentPangrams.length,
  }

  // ── Monthly stats ─────────────────────────────────────────────────────────
  const monthlyMap = new Map<string, { games: Game[] }>()
  for (const g of games) {
    const month = g.puzzle_date.slice(0, 7) // YYYY-MM
    if (!monthlyMap.has(month)) monthlyMap.set(month, { games: [] })
    monthlyMap.get(month)!.games.push(g)
  }

  const monthly: MonthStat[] = Array.from(monthlyMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, { games: mg }]) => {
      const withScore = mg.filter(g => g.max_possible_score && g.max_possible_score > 0)
      const withWords = mg.filter(g => g.total_possible_words && g.total_possible_words > 0)
      return {
        month,
        games:     mg.length,
        score_pct: round(avg(withScore.map(g => g.score / g.max_possible_score! * 100)), 1),
        words_pct: round(avg(withWords.map(g => g.total_words_found / g.total_possible_words! * 100)), 1),
        genius:    mg.filter(g => g.is_genius).length,
        qb:        mg.filter(g => g.is_queen_bee).length,
      }
    })

  // ── Weekly stats ──────────────────────────────────────────────────────────
  // Calendar weeks (Mon–Sun). Weeks with no games played are simply absent
  // from the array rather than plotted as a zero — data gaps become gaps
  // in the line, not dips to 0%.
  const weeklyMap = new Map<string, { games: Game[] }>()
  for (const g of games) {
    const week = weekStart(g.puzzle_date)
    if (!weeklyMap.has(week)) weeklyMap.set(week, { games: [] })
    weeklyMap.get(week)!.games.push(g)
  }

  const weekly: WeekStat[] = Array.from(weeklyMap.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([week, { games: wg }]) => {
      const withScore = wg.filter(g => g.max_possible_score && g.max_possible_score > 0)
      const withWords = wg.filter(g => g.total_possible_words && g.total_possible_words > 0)
      return {
        week,
        games:     wg.length,
        score_pct: round(avg(withScore.map(g => g.score / g.max_possible_score! * 100)), 1),
        words_pct: round(avg(withWords.map(g => g.total_words_found / g.total_possible_words! * 100)), 1),
        genius:    wg.filter(g => g.is_genius).length,
        qb:        wg.filter(g => g.is_queen_bee).length,
      }
    })

  // ── Miss by length ────────────────────────────────────────────────────────
  // Computed over three windows — last 7 games, last 30 games, all time —
  // using game counts rather than calendar days so gaps in play history
  // don't shrink the window below what it's supposed to cover.
  function computeMissByLength(answers: PuzzleAnswer[]): LengthStat[] {
    const lengthMap = new Map<number, { total: number; missed: number }>()
    for (const pa of answers) {
      const lenGroup = pa.length >= 8 ? 8 : pa.length
      const found = foundByGame.get(pa.game_id)?.has(pa.word) ?? false
      const curr = lengthMap.get(lenGroup) ?? { total: 0, missed: 0 }
      curr.total++
      if (!found) curr.missed++
      lengthMap.set(lenGroup, curr)
    }
    return Array.from(lengthMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([len, { total, missed }]) => ({
        length:   len,
        label:    len >= 8 ? '8+ letter' : `${len}-letter`,
        total,
        missed,
        miss_pct: total > 0 ? round(missed / total * 100, 1) : 0,
      }))
  }

  const last30Ids = new Set(games.slice(-30).map(g => g.id))

  const miss_by_length: MissByLength = {
    last7:  computeMissByLength(puzzleAnswers.filter(pa => recentIds.has(pa.game_id))),
    last30: computeMissByLength(puzzleAnswers.filter(pa => last30Ids.has(pa.game_id))),
    all:    computeMissByLength(puzzleAnswers),
  }

  // ── Study words ───────────────────────────────────────────────────────────
  const wordMap = new Map<string, {
    appearances: number
    missed: number
    lastMissed: string | null
    length: number
    isPangram: boolean
  }>()

  for (const pa of puzzleAnswers) {
    const game = gameById.get(pa.game_id)
    if (!game) continue
    const isMissed = !(foundByGame.get(pa.game_id)?.has(pa.word) ?? false)
    const existing = wordMap.get(pa.word)
    if (!existing) {
      wordMap.set(pa.word, {
        appearances: 1,
        missed:      isMissed ? 1 : 0,
        lastMissed:  isMissed ? game.puzzle_date : null,
        length:      pa.length,
        isPangram:   pa.is_pangram,
      })
    } else {
      existing.appearances++
      if (isMissed) {
        existing.missed++
        if (!existing.lastMissed || game.puzzle_date > existing.lastMissed) {
          existing.lastMissed = game.puzzle_date
        }
      }
      existing.isPangram = existing.isPangram || pa.is_pangram
    }
  }

  // Note: no minimum-appearances requirement here — a word missed on its only
  // appearance so far still belongs on the study list. The goal isn't just
  // spotting repeat spelling-bee weak spots, it's building vocabulary in
  // general, so a first-time miss is just as worth surfacing as a recurring
  // one. (Previously this required appearances >= 2, which silently hid any
  // word you'd only seen once — including ones missed within the last few
  // days.) Repeat misses still naturally rank higher via the weight formula
  // below, since `appearances` factors in directly.
  // Pangrams are excluded — they already get their own "Missed pangrams" card,
  // so including them here would just be duplicate real estate. (The old
  // pangram-bonus multiplier in the weight formula is dropped too, since it's
  // now a no-op — every word left in this list is a non-pangram by construction.)
  const study_words: StudyWord[] = Array.from(wordMap.entries())
    .filter(([, w]) => w.missed > 0 && !w.isPangram)
    .map(([word, w]) => {
      const missPct = round(w.missed / w.appearances * 100, 1)
      const weight = round(
        (w.missed / w.appearances) * (w.length / 4) * (w.appearances / 3),
        2
      )
      return {
        word,
        appearances: w.appearances,
        missed:      w.missed,
        miss_pct:    missPct,
        length:      w.length,
        is_pangram:  w.isPangram,
        weight,
        last_missed: w.lastMissed,
        definition:  DEFINITIONS[word] ?? dbDefinitions.get(word) ?? '',
      }
    })
    .sort((a, b) => b.weight - a.weight || b.miss_pct - a.miss_pct)
  // Not sliced to a fixed count here — the dashboard applies the top-100 cap
  // only to the "all time" bucket, after splitting out recently-missed words,
  // so a fresh miss can't be pushed off the list by its own low weight before
  // it's had a chance to recur. See Dashboard.tsx.

  // Any word actually visible on the dashboard (recent misses, unbounded but
  // naturally small since the window is only 7 days, plus the top-100 all-time
  // words) that still has no definition is either a brand new study word since
  // the last backfill, or genuinely absent from the dictionary API (slang/
  // informal answers). Look those up now and cache hits for next time. This is
  // deliberately scoped to what's rendered rather than the full study_words
  // list — study_words is no longer capped (see above), so without this scope
  // a bad week could trigger hundreds of concurrent dictionary lookups.
  const defCutoff = new Date()
  defCutoff.setDate(defCutoff.getDate() - 7)
  const defCutoffStr = defCutoff.toISOString().slice(0, 10)
  const visibleStudyWords = [
    ...study_words.filter(w => w.last_missed && w.last_missed >= defCutoffStr),
    ...study_words.slice(0, 100),
  ]
  const undefinedWords = Array.from(new Set(visibleStudyWords.filter(w => !w.definition).map(w => w.word)))
  if (undefinedWords.length > 0) {
    const lookups = await Promise.all(
      undefinedWords.map(async word => ({ word, definition: await lookupDictionaryDefinition(word) }))
    )
    const newlyCached = lookups.filter(l => l.definition) as { word: string; definition: string }[]
    if (newlyCached.length > 0) {
      const byWord = new Map(newlyCached.map(l => [l.word, l.definition]))
      for (const w of study_words) {
        const def = byWord.get(w.word)
        if (def) w.definition = def
      }
      await supabase.from('word_definitions').upsert(
        newlyCached.map(l => ({ word: l.word, definition: l.definition, source: 'dictionaryapi.dev' }))
      )
    }
  }

  // ── Missed pangrams ───────────────────────────────────────────────────────
  const missed_pangrams: MissedPangram[] = puzzleAnswers
    .filter(pa => pa.is_pangram && !(foundByGame.get(pa.game_id)?.has(pa.word) ?? false))
    .map(pa => {
      const game = gameById.get(pa.game_id)!
      return { word: pa.word, date: game.puzzle_date, points: pa.points, length: pa.length }
    })
    .sort((a, b) => b.date.localeCompare(a.date))

  return {
    generated_at:   new Date().toISOString(),
    summary,
    recent,
    monthly,
    weekly,
    miss_by_length,
    study_words,
    missed_pangrams,
  }
}

import { supabase } from './supabase'

// Fetch all rows from a table, paginating past Supabase's 1000-row default limit
async function fetchAll<T>(
  query: () => ReturnType<typeof supabase.from>
): Promise<T[]> {
  const PAGE = 1000
  let offset = 0
  const results: T[] = []
  while (true) {
    const { data, error } = await (query() as any).range(offset, offset + PAGE - 1)
    if (error) throw new Error(error.message)
    results.push(...(data as T[]))
    if (data.length < PAGE) break
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

export type LengthStat = {
  length: number
  label: string
  total: number
  missed: number
  miss_pct: number
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
  miss_by_length: LengthStat[]
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

// ── Main analytics function ───────────────────────────────────────────────────

export async function getAnalytics(): Promise<AnalyticsData> {
  // Fetch all data (paginated to bypass 1000-row default limit)
  const [games, wordsFound, puzzleAnswers] = await Promise.all([
    fetchAll<Game>(() => supabase.from('games').select('*').order('puzzle_date', { ascending: true })),
    fetchAll<WordFound>(() => supabase.from('words_found').select('game_id, word, is_pangram, length')),
    fetchAll<PuzzleAnswer>(() => supabase.from('puzzle_answers').select('game_id, word, points, is_pangram, length')),
  ])

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

  // ── Miss by length ────────────────────────────────────────────────────────
  const lengthMap = new Map<number, { total: number; missed: number }>()
  for (const pa of puzzleAnswers) {
    const lenGroup = pa.length >= 8 ? 8 : pa.length
    const found = foundByGame.get(pa.game_id)?.has(pa.word) ?? false
    const curr = lengthMap.get(lenGroup) ?? { total: 0, missed: 0 }
    curr.total++
    if (!found) curr.missed++
    lengthMap.set(lenGroup, curr)
  }

  const miss_by_length: LengthStat[] = Array.from(lengthMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([len, { total, missed }]) => ({
      length:   len,
      label:    len >= 8 ? '8+ letter' : `${len}-letter`,
      total,
      missed,
      miss_pct: total > 0 ? round(missed / total * 100, 1) : 0,
    }))

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

  const study_words: StudyWord[] = Array.from(wordMap.entries())
    .filter(([, w]) => w.appearances >= 2 && w.missed > 0)
    .map(([word, w]) => {
      const missPct = round(w.missed / w.appearances * 100, 1)
      const weight = round(
        (w.missed / w.appearances) * (w.length / 4) * (w.isPangram ? 3 : 1) * (w.appearances / 3),
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
        definition:  DEFINITIONS[word] ?? '',
      }
    })
    .sort((a, b) => b.weight - a.weight || b.miss_pct - a.miss_pct)
    .slice(0, 100)

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
    miss_by_length,
    study_words,
    missed_pangrams,
  }
}

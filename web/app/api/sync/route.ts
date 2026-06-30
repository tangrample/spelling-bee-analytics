import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabaseAdmin'
import { parseNYTData } from '@/lib/parseNYTData'

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Sync-Secret',
}

// Handle preflight
export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS })
}

export async function POST(req: NextRequest) {
  // ── Auth ────────────────────────────────────────────────────────────────────
  const secret = req.headers.get('x-sync-secret')
  if (!secret || secret !== process.env.SYNC_SECRET) {
    return NextResponse.json({ ok: false, error: 'Unauthorized' }, { status: 401, headers: CORS })
  }

  // ── Parse body ──────────────────────────────────────────────────────────────
  let rawData: Record<string, unknown>
  try {
    rawData = await req.json()
  } catch {
    return NextResponse.json({ ok: false, error: 'Invalid JSON' }, { status: 400, headers: CORS })
  }

  // ── Parse NYT data ──────────────────────────────────────────────────────────
  const games = parseNYTData(rawData)
  if (games.length === 0) {
    return NextResponse.json({ ok: false, error: 'No games found in data' }, { status: 400, headers: CORS })
  }

  // ── Upsert each game ────────────────────────────────────────────────────────
  const results: { date: string; ok: boolean; error?: string }[] = []

  for (const { gameRecord, wordsFound, puzzleAnswers } of games) {
    try {
      // Check if game already exists
      const { data: existing } = await supabaseAdmin
        .from('games')
        .select('id')
        .eq('puzzle_date', gameRecord.puzzle_date)
        .is('user_id', null)
        .maybeSingle()

      let gameId: number

      if (existing) {
        // Update existing game
        const { error } = await supabaseAdmin
          .from('games')
          .update(gameRecord)
          .eq('id', existing.id)
        if (error) throw error
        gameId = existing.id
      } else {
        // Insert new game
        const { data, error } = await supabaseAdmin
          .from('games')
          .insert(gameRecord)
          .select('id')
          .single()
        if (error) throw error
        gameId = data.id
      }

      // Upsert words found
      if (wordsFound.length > 0) {
        const { error } = await supabaseAdmin
          .from('words_found')
          .upsert(
            wordsFound.map(w => ({ ...w, game_id: gameId })),
            { onConflict: 'game_id,word' }
          )
        if (error) throw error
      }

      // Upsert puzzle answers (only present when puzzle is revealed)
      if (puzzleAnswers.length > 0) {
        const { error } = await supabaseAdmin
          .from('puzzle_answers')
          .upsert(
            puzzleAnswers.map(w => ({ ...w, game_id: gameId })),
            { onConflict: 'game_id,word' }
          )
        if (error) throw error
      }

      results.push({ date: gameRecord.puzzle_date, ok: true })
    } catch (err) {
      results.push({ date: gameRecord.puzzle_date, ok: false, error: String(err) })
    }
  }

  const saved = results.filter(r => r.ok).length
  return NextResponse.json({ ok: true, saved, total: games.length, results }, { headers: CORS })
}

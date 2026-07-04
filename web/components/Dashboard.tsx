'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { AnalyticsData, StudyWord, MissedPangram, MonthStat, LengthStat } from '@/lib/analytics'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso + 'T12:00:00').toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

function fmtMonthShort(ym: string) {
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return months[parseInt(ym.split('-')[1]) - 1]
}

function missBadge(pct: number) {
  return pct >= 80 ? 'badge badge-red' : pct >= 50 ? 'badge badge-amber' : 'badge badge-teal'
}

function lenBadge(len: number) {
  return len >= 10 ? 'badge badge-purple' : len >= 8 ? 'badge badge-amber' : 'badge badge-teal'
}

function barColor(pct: number) {
  return pct >= 28 ? 'var(--red)' : pct >= 20 ? 'var(--amber)' : 'var(--teal)'
}

function barH(val: number, minY = 60, maxY = 90) {
  const yRange = maxY - minY
  return Math.max(0, Math.min(100, (val - minY) / yRange * 100)).toFixed(1) + '%'
}

// ── Sub-components ────────────────────────────────────────────────────────────

function WordRow({ w, showDate }: { w: StudyWord; showDate: boolean }) {
  const dateBadge = showDate && w.last_missed
    ? new Date(w.last_missed + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    : null

  return (
    <div className="word-row">
      <div className="word-left">
        <span className="word-name">{w.word}</span>
        <span className={missBadge(w.miss_pct)}>{w.miss_pct}% · {w.appearances}×</span>
        {dateBadge && <span className="badge badge-date">{dateBadge}</span>}
      </div>
      <span className="word-def">{w.definition || `${w.length}-letter word`}</span>
    </div>
  )
}

function PangramRow({ p }: { p: MissedPangram }) {
  const dt = new Date(p.date + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return (
    <div className="word-row">
      <div className="word-left">
        <span className="word-name">{p.word}</span>
        <span className={lenBadge(p.length)}>{p.length} letters</span>
      </div>
      <span className="word-def">{dt}</span>
    </div>
  )
}

function MonthlyChart({ monthly }: { monthly: MonthStat[] }) {
  const lastM = monthly[monthly.length - 1]
  const bestM = monthly.reduce((b, m) => m.score_pct > b.score_pct ? m : b, monthly[0])
  const insight = lastM.score_pct >= bestM.score_pct
    ? `Trending up — ${fmtMonthShort(lastM.month)} is your strongest month yet (${lastM.score_pct}%).`
    : `Best month so far: ${fmtMonthShort(bestM.month)} at ${bestM.score_pct}%.`

  return (
    <div className="slide">
      <div className="chart-header">
        <span className="chart-title">Score &amp; words found % by month</span>
        <div className="legend">
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--teal)' }} />Score %
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--teal-light)' }} />Words %
          </div>
        </div>
      </div>
      <div className="chart-area">
        <div className="chart-body">
          <div className="y-axis">
            <span className="y-label">90%</span>
            <span className="y-label">75%</span>
            <span className="y-label">60%</span>
          </div>
          <div className="bars">
            <div className="grid-line" style={{ top: 0 }} />
            <div className="grid-line" style={{ top: '50%' }} />
            {monthly.map(m => (
              <div key={m.month} className="bar-group">
                <div className="bar" style={{ height: barH(m.score_pct), background: 'var(--teal)' }} data-val={`${m.score_pct}%`} />
                <div className="bar" style={{ height: barH(m.words_pct), background: 'var(--teal-light)' }} data-val={`${m.words_pct}%`} />
              </div>
            ))}
          </div>
        </div>
        <div className="x-labels">
          {monthly.map(m => (
            <span key={m.month} className="x-label">{fmtMonthShort(m.month)}</span>
          ))}
        </div>
      </div>
      <p className="insight">{insight}</p>
    </div>
  )
}

function LengthSlide({ missByLength }: { missByLength: LengthStat[] }) {
  return (
    <div className="slide">
      <div className="slide-label">Miss rate by word length</div>
      <div className="len-rows">
        {missByLength.map(r => (
          <div key={r.length}>
            <div className="len-header">
              <span className="len-label">{r.label}</span>
              <span className="len-pct" style={{ color: barColor(r.miss_pct) }}>{r.miss_pct.toFixed(0)}%</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${r.miss_pct}%`, background: barColor(r.miss_pct) }} />
            </div>
          </div>
        ))}
      </div>
      <p className="insight">Mostly cheap losses — 4-letter words are only worth 1 pt.</p>
    </div>
  )
}

// ── Bee SVG ───────────────────────────────────────────────────────────────────

function BeeSvg() {
  return (
    <svg width="82" height="44" viewBox="0 0 82 44" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" style={{ flexShrink: 0 }}>
      <defs>
        <clipPath id="hL"><ellipse cx="13" cy="34" rx="9" ry="9"/></clipPath>
        <clipPath id="hR"><ellipse cx="69" cy="34" rx="9" ry="9"/></clipPath>
      </defs>
      <ellipse cx="3"  cy="25" rx="5.5" ry="3" fill="white" stroke="#222" strokeWidth="1" opacity=".85"/>
      <ellipse cx="21" cy="25" rx="5.5" ry="3" fill="white" stroke="#222" strokeWidth="1" opacity=".85"/>
      <ellipse cx="13" cy="34" rx="9" ry="9" fill="#F5C833" stroke="#222" strokeWidth="1.4"/>
      <rect x="4"  y="30.5" width="18" height="3.5" fill="#333" clipPath="url(#hL)"/>
      <rect x="4"  y="36.5" width="18" height="3.5" fill="#333" clipPath="url(#hL)"/>
      <circle cx="13" cy="20" r="5.5" fill="#F5C833" stroke="#222" strokeWidth="1.4"/>
      <circle cx="11" cy="19.5" r="1" fill="#222"/>
      <circle cx="15" cy="19.5" r="1" fill="#222"/>
      <path d="M11,15 Q9,12 8,10.5" stroke="#222" strokeWidth="1" fill="none" strokeLinecap="round"/>
      <circle cx="7.5" cy="10" r="1" fill="#222"/>
      <path d="M15,15 Q17,12 18,10.5" stroke="#222" strokeWidth="1" fill="none" strokeLinecap="round"/>
      <circle cx="18.5" cy="10" r="1" fill="#222"/>
      <path d="M1,16 Q6,19.5 13,18 Q20,19.5 25,16 Q22,13.5 13,14.5 Q4,13.5 1,16 Z" fill="#D4A017" stroke="#222" strokeWidth="0.9"/>
      <path d="M6.5,16 Q7.5,10 12,9 Q15.5,8.5 19.5,16 Z" fill="#E8B820" stroke="#222" strokeWidth="0.9"/>
      <rect x="7" y="14.8" width="12" height="1.5" fill="#B8860B"/>
      <path d="M20,26 Q26,22 34,19" stroke="#F5C833" strokeWidth="3" strokeLinecap="round" fill="none"/>
      <path d="M20,26 Q26,22 34,19" stroke="#222" strokeWidth="4" strokeLinecap="round" fill="none" opacity="0.1"/>
      <rect x="35" y="15.5" width="6" height="5.5" rx="1.8" fill="#F5C833" stroke="#222" strokeWidth="1.1"/>
      <line x1="37.5" y1="15.5" x2="37.5" y2="21" stroke="#222" strokeWidth="0.5" opacity="0.4"/>
      <line x1="39.5" y1="15.5" x2="39.5" y2="21" stroke="#222" strokeWidth="0.5" opacity="0.4"/>
      <ellipse cx="61" cy="25" rx="5.5" ry="3" fill="white" stroke="#222" strokeWidth="1" opacity=".85"/>
      <ellipse cx="79" cy="25" rx="5.5" ry="3" fill="white" stroke="#222" strokeWidth="1" opacity=".85"/>
      <ellipse cx="69" cy="34" rx="9" ry="9" fill="#F5C833" stroke="#222" strokeWidth="1.4"/>
      <rect x="60" y="30.5" width="18" height="3.5" fill="#333" clipPath="url(#hR)"/>
      <rect x="60" y="36.5" width="18" height="3.5" fill="#333" clipPath="url(#hR)"/>
      <circle cx="69" cy="20" r="5.5" fill="#F5C833" stroke="#222" strokeWidth="1.4"/>
      <circle cx="67" cy="19.5" r="1" fill="#222"/>
      <circle cx="71" cy="19.5" r="1" fill="#222"/>
      <path d="M67,15.5 Q65,12.5 64,11" stroke="#222" strokeWidth="1" fill="none" strokeLinecap="round"/>
      <circle cx="63.5" cy="10.5" r="1" fill="#222"/>
      <path d="M71,15.5 Q73,12.5 74,11" stroke="#222" strokeWidth="1" fill="none" strokeLinecap="round"/>
      <circle cx="74.5" cy="10.5" r="1" fill="#222"/>
      <path d="M63.5,16.5 Q63.5,10.5 69,10.5 Q74.5,10.5 74.5,16.5 Z" fill="#CC2222" stroke="#222" strokeWidth="0.9"/>
      <rect x="63.5" y="15" width="11" height="2.5" rx="1.2" fill="#AA1515" stroke="#222" strokeWidth="0.8"/>
      <circle cx="69" cy="10.5" r="2.5" fill="#DD3333" stroke="#222" strokeWidth="0.8"/>
      <circle cx="69" cy="10.5" r="1.1" fill="#FF6666"/>
      <path d="M62,26 Q56,22 48,19" stroke="#F5C833" strokeWidth="3" strokeLinecap="round" fill="none"/>
      <path d="M62,26 Q56,22 48,19" stroke="#222" strokeWidth="4" strokeLinecap="round" fill="none" opacity="0.1"/>
      <rect x="41" y="15.5" width="6" height="5.5" rx="1.8" fill="#F5C833" stroke="#222" strokeWidth="1.1"/>
      <line x1="43.5" y1="15.5" x2="43.5" y2="21" stroke="#222" strokeWidth="0.5" opacity="0.4"/>
      <line x1="45.5" y1="15.5" x2="45.5" y2="21" stroke="#222" strokeWidth="0.5" opacity="0.4"/>
      <line x1="41" y1="16" x2="39" y2="14" stroke="#E8B820" strokeWidth="1.4" strokeLinecap="round"/>
      <line x1="41" y1="19" x2="39" y2="21" stroke="#E8B820" strokeWidth="1.4" strokeLinecap="round"/>
      <line x1="41" y1="17.5" x2="38.5" y2="17.5" stroke="#E8B820" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  )
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

const SLIDE_COUNT = 5

export default function Dashboard({ data }: { data: AnalyticsData }) {
  const { summary: s, recent: rc, study_words, missed_pangrams, monthly, miss_by_length } = data
  const hasRecent = (rc.games ?? 0) > 0

  const [cur, setCur] = useState(0)
  const touchStartX = useRef<number | null>(null)

  const goTo = useCallback((i: number) => {
    setCur(Math.max(0, Math.min(SLIDE_COUNT - 1, i)))
  }, [])

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft')  goTo(cur - 1)
      if (e.key === 'ArrowRight') goTo(cur + 1)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [cur, goTo])

  // Touch swipe
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
  }
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return
    const dx = e.changedTouches[0].clientX - touchStartX.current
    if (Math.abs(dx) > 50) goTo(cur + (dx < 0 ? 1 : -1))
    touchStartX.current = null
  }

  // ── Recent word cutoff (7 days) ──────────────────────────────
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 7)
  const cutoffStr = cutoff.toISOString().slice(0, 10)
  const recentWords  = study_words.filter(w => w.last_missed && w.last_missed >= cutoffStr)
  const allTimeWords = study_words.filter(w => !w.last_missed || w.last_missed < cutoffStr)

  // ── Study words insight ──────────────────────────────────────
  const topWord = study_words[0]
  const studyInsight = topWord
    ? topWord.miss_pct === 100
      ? `${topWord.word} has appeared ${topWord.appearances}× — you've never found it.`
      : `${topWord.word} tops the list — missed ${topWord.miss_pct}% of ${topWord.appearances} appearances.`
    : ''

  // ── Overview stat cell ───────────────────────────────────────
  function OverviewStat({ label, weekFmt, allTimeFmt, color }: {
    label: string; weekFmt: string; allTimeFmt: string; color?: string
  }) {
    return (
      <div>
        <p className="stat-label">{label}</p>
        {hasRecent ? (
          <>
            <p className="stat-big" style={color ? { color } : undefined}>
              {weekFmt}<span className="stat-week">this week</span>
            </p>
            <p className="stat-alltime">{allTimeFmt} all time</p>
          </>
        ) : (
          <>
            <p className="stat-big" style={color ? { color } : undefined}>{allTimeFmt}</p>
            <p className="stat-alltime">across all {s.total_games} games</p>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <div className="header-left">
          <img src="/icon.png" alt="BeeBot" width={44} height={44} style={{ borderRadius: '50%', flexShrink: 0 }} />
          <div>
            <h1>BeeBot</h1>
            <div className="meta">{s.total_games} games · {fmtDate(s.first_date)} – {fmtDate(s.last_date)}</div>
          </div>
        </div>
        <span className="slide-counter">{cur + 1} / {SLIDE_COUNT}</span>
      </div>

      {/* Carousel */}
      <div className="carousel-outer">
        <div
          className="carousel-track"
          style={{ transform: `translateX(-${cur * 100}%)` }}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          {/* Slide 1: Overview */}
          <div className="slide">
            <div className="slide-label">Overview</div>
            <div className="overview-grid">
              <OverviewStat
                label="Avg score"
                weekFmt={`${rc.avg_score_pct}%`}
                allTimeFmt={`${s.avg_score_pct}%`}
                color="var(--teal)"
              />
              <OverviewStat
                label="Genius rate"
                weekFmt={`${rc.genius_count}/${rc.games}`}
                allTimeFmt={`${s.genius_rate}%`}
              />
              <OverviewStat
                label="Pangrams found"
                weekFmt={`${rc.pangram_found}/${rc.pangram_total || '?'}`}
                allTimeFmt={`${s.pangram_pct}%`}
              />
              <OverviewStat
                label="Word miss rate"
                weekFmt={`${rc.word_miss_rate}%`}
                allTimeFmt={`${s.word_miss_rate}%`}
              />
            </div>
          </div>

          {/* Slide 2: Words to study */}
          <div className="slide slide-scroll">
            <div className="slide-label">Words to study</div>
            <div className="word-list">
              {recentWords.length > 0 && (
                <>
                  <div className="section-label">Recent</div>
                  {recentWords.map(w => <WordRow key={w.word} w={w} showDate={true} />)}
                  <div className="section-label spaced">All time · highest miss rate</div>
                </>
              )}
              {allTimeWords.map(w => <WordRow key={w.word} w={w} showDate={false} />)}
            </div>
            {studyInsight && <p className="insight">{studyInsight}</p>}
          </div>

          {/* Slide 3: Missed pangrams */}
          <div className="slide slide-scroll">
            <div className="slide-label">Missed pangrams — {s.pangram_missed} total</div>
            <div className="word-list">
              {missed_pangrams.map(p => <PangramRow key={`${p.word}-${p.date}`} p={p} />)}
            </div>
            <p className="insight">{s.pangram_miss_pct}% pangram miss rate — most are long compound words.</p>
          </div>

          {/* Slide 4: Monthly trend */}
          <MonthlyChart monthly={monthly} />

          {/* Slide 5: Miss by length */}
          <LengthSlide missByLength={miss_by_length} />
        </div>
      </div>

      {/* Nav */}
      <div className="carousel-nav">
        <button className="nav-btn" onClick={() => goTo(cur - 1)} disabled={cur === 0} aria-label="Previous">&#8249;</button>
        <div className="dots">
          {Array.from({ length: SLIDE_COUNT }, (_, i) => (
            <div
              key={i}
              className={`dot${i === cur ? ' active' : ''}`}
              onClick={() => goTo(i)}
            />
          ))}
        </div>
        <button className="nav-btn" onClick={() => goTo(cur + 1)} disabled={cur === SLIDE_COUNT - 1} aria-label="Next">&#8250;</button>
      </div>

      {/* Footer */}
      <div className="footer">
        Reflects data from {s.total_games} puzzles ({fmtDate(s.first_date)} – {fmtDate(s.last_date)}).
        {' '}Word miss stats exclude {s.total_games - s.games_with_answers} games with incomplete data.
        <div style={{ marginTop: '0.4rem' }}>
          BeeBot is an independent fan project for Spelling Bee enthusiasts. Not affiliated with or endorsed by The New York Times.
        </div>
      </div>
    </div>
  )
}

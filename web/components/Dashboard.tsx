'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import type { AnalyticsData, StudyWord, MissedPangram, MonthStat, WeekStat, MissByLength } from '@/lib/analytics'

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

function fmtWeekShort(iso: string) {
  const d = new Date(iso + 'T12:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
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

type TrendPoint = { key: string; label: string; games: number; score_pct: number; words_pct: number }

function TrendChart({ weekly, monthly }: { weekly: WeekStat[]; monthly: MonthStat[] }) {
  const [range, setRange] = useState<'weekly' | 'monthly'>('weekly')

  const weeklyPoints: TrendPoint[] = weekly.map(w => ({
    key: w.week, label: fmtWeekShort(w.week), games: w.games, score_pct: w.score_pct, words_pct: w.words_pct,
  }))
  const monthlyPoints: TrendPoint[] = monthly.map(m => ({
    key: m.month, label: fmtMonthShort(m.month), games: m.games, score_pct: m.score_pct, words_pct: m.words_pct,
  }))
  const points = range === 'weekly' ? weeklyPoints : monthlyPoints
  const unit = range === 'weekly' ? 'week' : 'month'

  const last = points[points.length - 1]
  const best = points.reduce((b, p) => p.score_pct > b.score_pct ? p : b, points[0])
  const insight = last.score_pct >= best.score_pct
    ? `Trending up — ${last.label} is your strongest ${unit} yet (${last.score_pct}%).`
    : `Best ${unit} so far: ${best.label} at ${best.score_pct}%.`

  const [hover, setHover] = useState<number | null>(null)

  // ── Measure the actual rendered size so the SVG viewBox matches real
  // pixels 1:1 — otherwise on a narrow phone the whole coordinate system
  // (including text, dots, and the tooltip) scales down with the container
  // and becomes unreadably small, even though the surrounding HTML title
  // and legend stay full size.
  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 640, height: 220 })
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(entries => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) setSize({ width, height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // ── SVG line geometry ─────────────────────────────────────────────────
  const w = size.width, h = size.height, padL = 34, padR = 8, padT = 16, padB = 24
  const plotW = w - padL - padR, plotH = h - padT - padB
  const vals = points.flatMap(p => [p.score_pct, p.words_pct])
  const dataMin = Math.min(...vals)

  // Y-axis: max is always 100, three evenly spaced ticks. Step is the
  // smallest "nice" interval (20, 25, then 50) whose bottom tick still
  // covers the data with a little headroom — 60/80/100 for typical scores,
  // widening automatically to 50/75/100 or 0/50/100 if a week/month scores
  // much lower.
  const NICE_STEPS = [20, 25, 50]
  const step = NICE_STEPS.find(s => 100 - 2 * s <= dataMin) ?? 50
  const max = 100
  const min = max - 2 * step
  const yTicks = [min, min + step, max]

  const x = (i: number) => padL + (points.length === 1 ? 0 : (i / (points.length - 1)) * plotW)
  const y = (v: number) => padT + plotH - ((v - min) / (max - min || 1)) * plotH
  const linePath = (key: 'score_pct' | 'words_pct') =>
    points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(' ')

  // Thin out x-axis labels when there are many points (weekly view)
  const labelStep = points.length > 10 ? Math.ceil(points.length / 8) : 1

  const hoverPoint = hover !== null ? points[hover] : null
  const tooltipText = hoverPoint
    ? `${hoverPoint.label} · Score ${hoverPoint.score_pct}% · Words ${hoverPoint.words_pct}% · ${hoverPoint.games} game${hoverPoint.games === 1 ? '' : 's'}`
    : ''
  const tooltipW = Math.min(plotW, tooltipText.length * 5.6 + 16)

  return (
    <div className="slide">
      <div className="chart-header">
        <span className="chart-title">Score &amp; words found % by {unit}</span>
        <div className="range-toggle">
          <button
            className={range === 'weekly' ? 'range-btn active' : 'range-btn'}
            onClick={() => setRange('weekly')}
          >Weekly</button>
          <button
            className={range === 'monthly' ? 'range-btn active' : 'range-btn'}
            onClick={() => setRange('monthly')}
          >Monthly</button>
        </div>
        <div className="legend">
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--teal)' }} />Score %
          </div>
          <div className="legend-item">
            <div className="legend-dot" style={{ background: 'var(--teal-light)' }} />Words %
          </div>
        </div>
      </div>
      <div className="line-chart-area" ref={containerRef}>
        <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className="line-chart-svg">
          {yTicks.map((t, i) => (
            <line key={`grid-${i}`} x1={padL} y1={y(t)} x2={w - padR} y2={y(t)} className="line-grid" />
          ))}
          {yTicks.map((t, i) => (
            <text key={`ytick-${i}`} x={padL - 6} y={y(t)} dy={3} textAnchor="end" className="line-y-label">
              {Math.round(t)}%
            </text>
          ))}
          <path d={linePath('words_pct')} fill="none" stroke="var(--teal-light)" strokeWidth={2} />
          <path d={linePath('score_pct')} fill="none" stroke="var(--teal)" strokeWidth={2} />
          {points.map((p, i) => (
            <circle key={`w-${p.key}`} cx={x(i)} cy={y(p.words_pct)} r={2.5} fill="var(--teal-light)" />
          ))}
          {points.map((p, i) => (
            <circle key={`s-${p.key}`} cx={x(i)} cy={y(p.score_pct)} r={2.5} fill="var(--teal)" />
          ))}
          {hover !== null && (
            <line x1={x(hover)} y1={padT} x2={x(hover)} y2={padT + plotH} className="line-hover-guide" />
          )}
          {points.map((p, i) => (
            (i % labelStep === 0 || i === points.length - 1) ? (
              <text key={`l-${p.key}`} x={x(i)} y={h - 6} textAnchor="middle" className="line-x-label">{p.label}</text>
            ) : null
          ))}
          {points.map((p, i) => (
            <rect
              key={`hit-${p.key}`}
              x={x(i) - (plotW / Math.max(points.length - 1, 1)) / 2}
              y={padT}
              width={plotW / Math.max(points.length - 1, 1)}
              height={plotH}
              fill="transparent"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              onTouchStart={() => setHover(i)}
            />
          ))}
          {hoverPoint && (
            <g transform={`translate(${Math.min(Math.max(x(hover!) - tooltipW / 2, padL), w - padR - tooltipW)}, ${padT - 2})`}>
              <rect width={tooltipW} height={20} rx={4} className="line-tooltip-bg" />
              <text x={tooltipW / 2} y={14} textAnchor="middle" className="line-tooltip-text">{tooltipText}</text>
            </g>
          )}
        </svg>
      </div>
      <p className="insight">{insight}</p>
    </div>
  )
}

type LengthRange = 'last7' | 'last30' | 'all'

function LengthSlide({ missByLength }: { missByLength: MissByLength }) {
  const [range, setRange] = useState<LengthRange>('all')
  const data = missByLength[range]
  const rangeLabel = range === 'last7' ? 'last 7 games' : range === 'last30' ? 'last 30 games' : 'all time'

  return (
    <div className="slide">
      <div className="chart-header" style={{ marginBottom: '1.25rem' }}>
        <span className="slide-label" style={{ marginBottom: 0 }}>Miss rate by word length</span>
        <div className="range-toggle">
          <button
            className={range === 'last7' ? 'range-btn active' : 'range-btn'}
            onClick={() => setRange('last7')}
          >7 games</button>
          <button
            className={range === 'last30' ? 'range-btn active' : 'range-btn'}
            onClick={() => setRange('last30')}
          >30 games</button>
          <button
            className={range === 'all' ? 'range-btn active' : 'range-btn'}
            onClick={() => setRange('all')}
          >All time</button>
        </div>
      </div>
      <div className="len-rows">
        {data.map(r => (
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
      <p className="insight">Mostly cheap losses — 4-letter words are only worth 1 pt. ({rangeLabel})</p>
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
  const { summary: s, recent: rc, study_words, missed_pangrams, monthly, weekly, miss_by_length } = data
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

          {/* Slide 4: Score trend */}
          <TrendChart weekly={weekly} monthly={monthly} />

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

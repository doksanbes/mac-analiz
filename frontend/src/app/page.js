'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Clock, Trophy, AlertCircle } from 'lucide-react'

const STATUS_MAP = {
  SCHEDULED: { label: 'PLANLI', type: 'upcoming' },
  TIMED: { label: 'BA\u015eLAMADI', type: 'upcoming' },
  IN_PLAY: { label: 'CANLI', type: 'live' },
  PAUSED: { label: 'DEVRE ARASI', type: 'live' },
  FINISHED: { label: 'MA\u00c7 SONUCU', type: 'finished' },
  POSTPONED: { label: 'ERTELEND\u0130', type: 'finished' },
  CANCELLED: { label: '\u0130PTAL', type: 'finished' },
  SUSPENDED: { label: 'DURDURULDU', type: 'live' },
}

function getStatusInfo(status) {
  return STATUS_MAP[status] || { label: status, type: 'upcoming' }
}

function formatTime(utcDate) {
  try {
    const date = new Date(utcDate)
    return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return '--:--'
  }
}

function StatusBadge({ status }) {
  const info = getStatusInfo(status)
  const styles = {
    live: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    finished: 'bg-white/5 text-zinc-400 border-white/10',
    upcoming: 'bg-white/10 text-zinc-100 border-white/15',
  }

  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${styles[info.type]}`}
    >
      {info.type === 'live' && (
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-live" />
      )}
      {info.label}
    </span>
  )
}

function MiniFormDots({ form }) {
  if (!form) return null
  const labels = { G: 'Galibiyet', B: 'Beraberlik', M: 'Mağlubiyet' }
  return (
    <div className="flex items-center gap-1 mt-0.5">
      {form.split('').slice(0, 5).map((c, i) => {
        const colors = { G: 'bg-emerald-500', B: 'bg-amber-400', M: 'bg-red-500' }
        return colors[c] ? (
          <span
            key={i}
            role="img"
            aria-label={labels[c]}
            title={labels[c]}
            className={`w-2 h-2 rounded-full ${colors[c]}`}
          />
        ) : null
      })}
    </div>
  )
}

function MatchCard({ match, index, form }) {
  const homeScore = match.score?.fullTime?.home
  const awayScore = match.score?.fullTime?.away
  const hasScore = homeScore !== null && awayScore !== null
  const statusInfo = getStatusInfo(match.status)

  return (
    <Link
      href={`/match/${match.id}`}
      data-testid={`match-card-${match.id}`}
      className="block w-full animate-fade-in"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="rounded-2xl bg-surface-card border border-white/[0.08] p-6 flex flex-col gap-4 relative overflow-hidden transition-all duration-300 hover:bg-surface-elevated hover:border-white/20 hover:-translate-y-1 hover:shadow-[0_8px_32px_rgba(0,0,0,0.4)] cursor-pointer h-full">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">

            <span className="text-xs font-bold uppercase tracking-[0.15em] text-zinc-500">
              {match.competition?.name || 'Bilinmeyen Lig'}
            </span>
          </div>
          <StatusBadge status={match.status} />
        </div>

        <div className="flex flex-col gap-3 flex-1">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">

              <div className="flex flex-col">
                <span className="text-base font-semibold text-white">
                  {match.homeTeam?.shortName || match.homeTeam?.name || 'Ev Sahibi'}
                </span>
                <MiniFormDots form={form?.home_form} />
              </div>
            </div>
            {hasScore && (
              <span className={`text-2xl font-black font-outfit tracking-tight ${statusInfo.type === 'live' ? 'text-emerald-400' : 'text-white'}`}>
                {homeScore}
              </span>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">

              <div className="flex flex-col">
                <span className="text-base font-semibold text-white">
                  {match.awayTeam?.shortName || match.awayTeam?.name || 'Deplasman'}
                </span>
                <MiniFormDots form={form?.away_form} />
              </div>
            </div>
            {hasScore && (
              <span className={`text-2xl font-black font-outfit tracking-tight ${statusInfo.type === 'live' ? 'text-emerald-400' : 'text-white'}`}>
                {awayScore}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 pt-2 border-t border-white/[0.06]">
          <Clock className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-xs text-zinc-500 font-medium">
            {formatTime(match.utcDate)}
          </span>
          {match.matchday && (
            <>
              <span className="text-zinc-600">&middot;</span>
              <span className="text-xs text-zinc-500 font-medium">
                Hafta {match.matchday}
              </span>
            </>
          )}
        </div>
      </div>
    </Link>
  )
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl bg-surface-card border border-white/[0.08] p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="skeleton w-32 h-4" />
        <div className="skeleton w-20 h-6 rounded-full" />
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div className="skeleton w-7 h-7 rounded-full" />
          <div className="skeleton w-28 h-5" />
        </div>
        <div className="flex items-center gap-3">
          <div className="skeleton w-7 h-7 rounded-full" />
          <div className="skeleton w-24 h-5" />
        </div>
      </div>
      <div className="skeleton w-20 h-3 mt-2" />
    </div>
  )
}

export default function Home() {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [formMap, setFormMap] = useState({})

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL || ''
    fetch(`${apiUrl}/api/matches`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.detail || 'Veri al\u0131namad\u0131')
        }
        return data
      })
      .then(data => {
        setMatches(data.matches || [])
        setLoading(false)
      })
      .catch(err => {
        setError(err.message || 'Veri al\u0131namad\u0131')
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    if (matches.length === 0) return
    const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL || ''
    fetch(`${apiUrl}/api/matches/form`)
      .then(res => res.ok ? res.json() : {})
      .then(data => setFormMap(data))
      .catch(() => {})
  }, [matches])

  return (
    <div className="min-h-screen">
      <section className="relative py-16 sm:py-24">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: "radial-gradient(ellipse at top, #064e3b 0%, #0a0a0a 75%)" }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/80 via-black/70 to-surface-base" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1
            data-testid="page-title"
            className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tighter text-white font-outfit"
          >
            G&#252;n&#252;n Ma&#231;lar&#305;
          </h1>
          <p className="mt-4 text-lg text-zinc-400 max-w-xl leading-relaxed">
            En g&#252;ncel futbol kar&#351;&#305;la&#351;malar&#305; ve canl&#305; skorlar.
          </p>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 -mt-4">
        {loading && (
          <div data-testid="loading-state" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {error && (
          <div
            data-testid="error-state"
            className="rounded-2xl bg-surface-card border border-red-500/20 p-8 flex flex-col items-center gap-4 text-center max-w-lg mx-auto"
          >
            <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-white font-outfit">Veri Al&#305;namad&#305;</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">{error}</p>
            <button
              data-testid="retry-button"
              onClick={() => window.location.reload()}
              className="mt-2 bg-emerald-500 text-white hover:bg-emerald-600 rounded-xl px-6 py-3 font-semibold transition-colors text-sm"
            >
              Tekrar Dene
            </button>
          </div>
        )}

        {!loading && !error && matches.length === 0 && (
          <div
            data-testid="empty-state"
            className="rounded-2xl bg-surface-card border border-white/[0.08] p-12 flex flex-col items-center gap-4 text-center max-w-lg mx-auto"
          >
            <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center">
              <Trophy className="w-6 h-6 text-zinc-500" />
            </div>
            <h3 className="text-lg font-semibold text-white font-outfit">Ma&#231; Bulunamad&#305;</h3>
            <p className="text-sm text-zinc-500">Bug&#252;n i&#231;in planlanm&#305;&#351; ma&#231; bulunmuyor.</p>
          </div>
        )}

        {!loading && !error && matches.length > 0 && (
          <div
            data-testid="matches-grid"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {matches.map((match, i) => (
              <MatchCard key={match.id} match={match} index={i} form={formMap[String(match.id)]} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

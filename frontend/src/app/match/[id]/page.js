'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Clock, Trophy, MapPin, AlertCircle, Calendar, FileText, Target, Shuffle, ShieldAlert } from 'lucide-react'

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

function formatDate(utcDate) {
  try {
    const date = new Date(utcDate)
    return date.toLocaleDateString('tr-TR', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return 'Tarih bilinmiyor'
  }
}

function formatTime(utcDate) {
  try {
    const date = new Date(utcDate)
    return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return '--:--'
  }
}

function InfoCard({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl bg-surface-card border border-white/[0.08] p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-zinc-500" />
        <span className="text-xs font-bold uppercase tracking-[0.15em] text-zinc-500">{label}</span>
      </div>
      <span className="text-sm font-semibold text-white">{value}</span>
    </div>
  )
}

function AnalysisCard({ icon: Icon, title, content, accentColor, index }) {
  return (
    <div
      data-testid={`analysis-card-${index}`}
      className="rounded-xl bg-surface-card border border-white/[0.08] p-6 flex flex-col gap-4 animate-fade-in transition-all duration-300 hover:border-white/15"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="flex items-center gap-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${accentColor}`}>
          <Icon className="w-4.5 h-4.5 text-white" />
        </div>
        <h3 className="text-base font-semibold text-white font-outfit">{title}</h3>
      </div>
      <p className="text-sm text-zinc-400 leading-relaxed">{content}</p>
    </div>
  )
}

function AnalysisSection({ matchId }) {
  const [analysis, setAnalysis] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(true)
  const [analysisError, setAnalysisError] = useState(null)

  useEffect(() => {
    if (!matchId) return
    const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL || ''
    fetch(`${apiUrl}/api/match/${matchId}/analysis`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Analiz verileri al\u0131namad\u0131')
        return data
      })
      .then(data => {
        setAnalysis(data)
        setAnalysisLoading(false)
      })
      .catch(err => {
        setAnalysisError(err.message)
        setAnalysisLoading(false)
      })
  }, [matchId])

  if (analysisLoading) {
    return (
      <div data-testid="analysis-loading" className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[0,1,2,3].map(i => (
          <div key={i} className="rounded-xl bg-surface-card border border-white/[0.08] p-6 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="skeleton w-9 h-9 rounded-lg" />
              <div className="skeleton w-28 h-5" />
            </div>
            <div className="flex flex-col gap-2">
              <div className="skeleton w-full h-3" />
              <div className="skeleton w-4/5 h-3" />
              <div className="skeleton w-3/5 h-3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (analysisError) {
    return (
      <div data-testid="analysis-error" className="rounded-xl bg-surface-card border border-red-500/20 p-6 flex items-center gap-3">
        <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
        <p className="text-sm text-zinc-400">{analysisError}</p>
      </div>
    )
  }

  if (!analysis) return null

  const cards = [
    { icon: FileText, title: 'Ma\u00e7 \u00d6zeti', content: analysis.mac_ozeti, color: 'bg-emerald-500/20' },
    { icon: Target, title: '\u00d6ne \u00c7\u0131kan Senaryo', content: analysis.one_cikan_senaryo, color: 'bg-sky-500/20' },
    { icon: Shuffle, title: 'Alternatif Senaryo', content: analysis.alternatif_senaryo, color: 'bg-amber-500/20' },
    { icon: ShieldAlert, title: 'Risk Notu', content: analysis.risk_notu, color: 'bg-red-500/20' },
  ]

  return (
    <div data-testid="analysis-grid" className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {cards.map((card, i) => (
        <AnalysisCard
          key={i}
          index={i}
          icon={card.icon}
          title={card.title}
          content={card.content}
          accentColor={card.color}
        />
      ))}
    </div>
  )
}

export default function MatchDetail() {
  const params = useParams()
  const [match, setMatch] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!params.id) return
    const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL || ''
    fetch(`${apiUrl}/api/match/${params.id}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.detail || 'Veri al\u0131namad\u0131')
        }
        return data
      })
      .then(data => {
        setMatch(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message || 'Veri al\u0131namad\u0131')
        setLoading(false)
      })
  }, [params.id])

  if (loading) {
    return (
      <div data-testid="loading-state" className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400 text-sm font-medium">Y&#252;kleniyor...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div data-testid="error-state" className="min-h-screen flex items-center justify-center px-4">
        <div className="rounded-2xl bg-surface-card border border-red-500/20 p-8 flex flex-col items-center gap-4 text-center max-w-lg">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-white font-outfit">Veri Al&#305;namad&#305;</h3>
          <p className="text-sm text-zinc-400">{error}</p>
          <Link
            href="/"
            data-testid="back-to-home-error"
            className="mt-2 bg-emerald-500 text-white hover:bg-emerald-600 rounded-xl px-6 py-3 font-semibold transition-colors text-sm"
          >
            Ana Sayfaya D&#246;n
          </Link>
        </div>
      </div>
    )
  }

  if (!match) {
    return (
      <div data-testid="not-found-state" className="min-h-screen flex items-center justify-center px-4">
        <div className="rounded-2xl bg-surface-card border border-white/[0.08] p-12 flex flex-col items-center gap-4 text-center max-w-lg">
          <Trophy className="w-8 h-8 text-zinc-500" />
          <h3 className="text-lg font-semibold text-white font-outfit">Ma&#231; Bulunamad&#305;</h3>
          <Link
            href="/"
            data-testid="back-to-home-notfound"
            className="mt-2 text-emerald-400 hover:text-emerald-300 text-sm font-medium transition-colors"
          >
            Ana Sayfaya D&#246;n
          </Link>
        </div>
      </div>
    )
  }

  const statusInfo = getStatusInfo(match.status)
  const homeScore = match.score?.fullTime?.home
  const awayScore = match.score?.fullTime?.away
  const hasScore = homeScore !== null && awayScore !== null
  const halfHome = match.score?.halfTime?.home
  const halfAway = match.score?.halfTime?.away
  const hasHalfScore = halfHome !== null && halfAway !== null

  return (
    <div className="min-h-screen">
      <section className="relative py-12 sm:py-20">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage: "url('https://images.pexels.com/photos/3991976/pexels-photo-3991976.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940')"
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/85 via-black/80 to-surface-base" />

        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <Link
            href="/"
            data-testid="back-button"
            className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-emerald-400 transition-colors mb-8 group"
          >
            <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
            Ma&#231;lara D&#246;n
          </Link>

          <div className="flex items-center gap-2 mb-6">
            {match.competition?.emblem && (
              <img src={match.competition.emblem} alt="" className="w-6 h-6 object-contain" />
            )}
            <span className="text-sm font-bold uppercase tracking-[0.15em] text-zinc-400">
              {match.competition?.name || 'Bilinmeyen Lig'}
            </span>
          </div>

          <div
            data-testid="match-scoreboard"
            className="rounded-2xl bg-surface-card/80 backdrop-blur-sm border border-white/[0.08] p-8 sm:p-10"
          >
            <div className="flex items-center justify-between gap-4">
              <div className="flex-1 flex flex-col items-center gap-3 text-center">
                {match.homeTeam?.crest && (
                  <img src={match.homeTeam.crest} alt="" className="w-14 h-14 sm:w-20 sm:h-20 object-contain" />
                )}
                <span
                  data-testid="home-team-name"
                  className="text-base sm:text-lg font-bold text-white font-outfit"
                >
                  {match.homeTeam?.name || 'Ev Sahibi'}
                </span>
              </div>

              <div className="flex flex-col items-center gap-2 px-4 sm:px-8">
                {hasScore ? (
                  <>
                    <div className={`text-4xl sm:text-5xl font-black font-outfit tracking-tighter ${statusInfo.type === 'live' ? 'text-emerald-400' : 'text-white'}`}>
                      <span data-testid="home-score">{homeScore}</span>
                      <span className="text-zinc-600 mx-2">-</span>
                      <span data-testid="away-score">{awayScore}</span>
                    </div>
                    {hasHalfScore && (
                      <span className="text-xs text-zinc-500">
                        &#304;Y: {halfHome} - {halfAway}
                      </span>
                    )}
                  </>
                ) : (
                  <span className="text-2xl sm:text-3xl font-bold text-zinc-600 font-outfit">vs</span>
                )}

                <span
                  data-testid="match-status-badge"
                  className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border mt-2
                    ${statusInfo.type === 'live'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : statusInfo.type === 'finished'
                        ? 'bg-white/5 text-zinc-400 border-white/10'
                        : 'bg-white/10 text-zinc-100 border-white/15'
                    }`}
                >
                  {statusInfo.type === 'live' && (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse-live" />
                  )}
                  {statusInfo.label}
                </span>
              </div>

              <div className="flex-1 flex flex-col items-center gap-3 text-center">
                {match.awayTeam?.crest && (
                  <img src={match.awayTeam.crest} alt="" className="w-14 h-14 sm:w-20 sm:h-20 object-contain" />
                )}
                <span
                  data-testid="away-team-name"
                  className="text-base sm:text-lg font-bold text-white font-outfit"
                >
                  {match.awayTeam?.name || 'Deplasman'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <h2 data-testid="match-info-title" className="text-2xl font-semibold tracking-tight text-white font-outfit mb-6">
          Ma&#231; Bilgileri
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          <InfoCard
            icon={Trophy}
            label="Lig"
            value={match.competition?.name || 'Bilinmiyor'}
          />
          <InfoCard
            icon={Calendar}
            label="Tarih"
            value={formatDate(match.utcDate)}
          />
          <InfoCard
            icon={Clock}
            label="Saat"
            value={formatTime(match.utcDate)}
          />
          <InfoCard
            icon={MapPin}
            label="Durum"
            value={statusInfo.label}
          />
        </div>

        <h2 data-testid="analysis-title" className="text-2xl font-semibold tracking-tight text-white font-outfit mb-6">
          Analiz
        </h2>

        <AnalysisSection matchId={params.id} />
      </section>
    </div>
  )
}

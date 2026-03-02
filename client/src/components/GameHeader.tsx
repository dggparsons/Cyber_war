import type { RoundTimer } from '../hooks/useRoundTimer'
import type { MegaChallengeData } from '../lib/api'
import { DoomsdayClock } from './DoomsdayClock'

type Props = {
  nationName: string
  role: string
  connected: boolean
  timer: RoundTimer
  timerDisplay: string
  timerProgress: number
  totalEscalation: number
  nextThreshold: number | null
  megaChallenge: MegaChallengeData | null
  timerState: string
  onViewBriefing: () => void
  onViewNations: () => void
  onViewMega: () => void
  onViewHelp: () => void
}

export function GameHeader({
  nationName, role, connected, timer, timerDisplay, timerProgress,
  totalEscalation, nextThreshold, megaChallenge, timerState,
  onViewBriefing, onViewNations, onViewMega, onViewHelp,
}: Props) {
  const statusChip = (() => {
    switch (timerState) {
      case 'running': return { label: 'SUBMISSIONS OPEN', color: 'text-emerald-400 border-emerald-400/40' }
      case 'paused': return { label: 'PAUSED', color: 'text-warroom-amber border-warroom-amber/40 animate-pulse' }
      case 'complete': return { label: 'RESOLVING', color: 'text-red-400 border-red-400/40' }
      default: return { label: 'WAITING', color: 'text-slate-400 border-slate-500/40' }
    }
  })()

  return (
    <header className="border-b border-slate-700 bg-warroom-slate/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest text-slate-400">Team</p>
          <h1 className="font-pixel text-lg text-warroom-cyan text-glow flex items-center gap-2">
            {nationName}
            <span className={`inline-block h-2 w-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-500'}`} title={connected ? 'Connected' : 'Disconnected'} />
          </h1>
          <p className="text-xs text-slate-400">Role: {role ?? 'player'}</p>
        </div>
        <div className="text-right space-y-2">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400">Round {timer.round}</p>
            <div className="flex items-center justify-end gap-2">
              <p className={`font-pixel text-xl text-warroom-amber ${timer.state === 'paused' ? 'animate-pulse' : ''}`}>{timerDisplay}</p>
              <span className={`rounded border px-2 py-0.5 text-[10px] uppercase tracking-widest ${statusChip.color}`}>{statusChip.label}</span>
            </div>
          </div>
          <div className="flex flex-col items-end gap-1">
            <div className="h-2 w-40 overflow-hidden rounded-full bg-slate-800/60">
              <div className={`h-2 rounded-full transition-all duration-300 ${timer.state === 'paused' ? 'bg-warroom-amber/70 animate-pulse' : 'bg-warroom-cyan'}`} style={{ width: `${(timerProgress * 100).toFixed(1)}%` }} />
            </div>
            {timer.state === 'paused' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Paused by GM</p>}
            {timer.state === 'complete' && <p className="text-[10px] uppercase tracking-widest text-slate-400">Submissions locked</p>}
            <p className="text-[10px] uppercase tracking-widest text-slate-400">Global Escalation: {totalEscalation}{nextThreshold ? ` → Next at ${nextThreshold}` : ''}</p>
            <DoomsdayClock escalation={totalEscalation} />
          </div>
          <div className="flex gap-2 justify-end">
            <button className="rounded border border-warroom-cyan/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-warroom-cyan hover:border-warroom-cyan" onClick={onViewBriefing}>View Briefing</button>
            <button className="rounded border border-warroom-amber/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-warroom-amber hover:border-warroom-amber" onClick={onViewNations}>Nations Intel</button>
            {megaChallenge?.active && (
              <button className="rounded border border-purple-400/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-purple-400 hover:border-purple-400" onClick={onViewMega}>Mega Challenge</button>
            )}
            <button className="rounded-full border border-slate-500 bg-warroom-blue/60 w-7 h-7 flex items-center justify-center text-sm font-bold text-slate-300 hover:border-warroom-cyan hover:text-warroom-cyan" onClick={onViewHelp} title="How to Play">?</button>
          </div>
        </div>
      </div>
    </header>
  )
}

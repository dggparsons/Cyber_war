import { useState, useCallback, useEffect } from 'react'
import {
  adminAdvanceRound,
  adminResetRounds,
  adminStartRound,
  adminPauseTimer,
  adminResumeTimer,
  adminFetchStatus,
  adminToggleNukes,
  adminInjectCrisis,
  adminClearCrisis,
  adminFullReset,
  vetoProposal,
  type GlobalStatePayload,
  type CrisisInfo,
  type ProposalPreview,
  type TimerPayload,
} from '../lib/api'
import { DEFAULT_GLOBAL_STATE } from '../lib/gameUtils'

type TeamSummary = { id: number; nation_name: string; nation_code: string; members: number; seat_cap: number }
type RoundSummary = { round_number: number; status: string; started_at: string | null }

export function AdminPanel() {
  const [message, setMessage] = useState<string | null>(null)
  const [messageType, setMessageType] = useState<'info' | 'error' | 'success'>('info')
  const [globalStatus, setGlobalStatus] = useState<GlobalStatePayload | null>(null)
  const [crisisHistory, setCrisisHistory] = useState<CrisisInfo[]>([])
  const [availableCrises, setAvailableCrises] = useState<CrisisInfo[]>([])
  const [selectedCrisis, setSelectedCrisis] = useState('')
  const [proposalPreview, setProposalPreview] = useState<any | null>(null)
  const [playerCount, setPlayerCount] = useState(0)
  const [teams, setTeams] = useState<TeamSummary[]>([])
  const [rounds, setRounds] = useState<RoundSummary[]>([])
  const [currentRound, setCurrentRound] = useState<number | null>(null)
  const [timer, setTimer] = useState<TimerPayload | null>(null)
  const [confirmFullReset, setConfirmFullReset] = useState(false)

  const flash = (msg: string, type: 'info' | 'error' | 'success' = 'info') => {
    setMessage(msg)
    setMessageType(type)
  }

  const refreshStatus = useCallback(async () => {
    try {
      const data = await adminFetchStatus()
      setGlobalStatus(data.global ?? DEFAULT_GLOBAL_STATE)
      setCrisisHistory(data.crises ?? [])
      setAvailableCrises(data.available_crises ?? [])
      setProposalPreview(data.proposal_preview ?? null)
      setPlayerCount(data.player_count ?? 0)
      setTeams(data.teams ?? [])
      setRounds(data.rounds ?? [])
      setCurrentRound(data.current_round ?? null)
      setTimer(data.timer ?? null)
    } catch (err) {
      console.error(err)
      flash('Failed to fetch status.', 'error')
    }
  }, [])

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 8000)
    return () => clearInterval(interval)
  }, [refreshStatus])

  const call = async (action: 'start' | 'advance' | 'reset' | 'pause' | 'resume') => {
    try {
      flash('Working...', 'info')
      if (action === 'start') {
        await adminStartRound()
        flash('Round started', 'success')
      } else if (action === 'advance') {
        await adminAdvanceRound()
        flash('Round resolved and advanced', 'success')
      } else if (action === 'reset') {
        await adminResetRounds()
        flash('Game state reset (players kept)', 'success')
      } else if (action === 'pause') {
        await adminPauseTimer()
        flash('Timer paused', 'success')
      } else if (action === 'resume') {
        await adminResumeTimer()
        flash('Timer resumed', 'success')
      }
      refreshStatus()
    } catch (err) {
      console.error(err)
      flash('Action failed.', 'error')
    }
  }

  const handleFullReset = async () => {
    try {
      flash('Full reset in progress...', 'info')
      await adminFullReset()
      flash('Full reset complete — all players removed, game wiped.', 'success')
      setConfirmFullReset(false)
      refreshStatus()
    } catch (err) {
      console.error(err)
      flash('Full reset failed.', 'error')
    }
  }

  const gmVetoProposal = async (proposalId: number) => {
    try {
      await vetoProposal(proposalId)
      flash('Veto issued', 'success')
      refreshStatus()
    } catch (err) {
      console.error(err)
      flash('Veto failed.', 'error')
    }
  }

  const toggleNukes = async () => {
    try {
      const unlocked = !(globalStatus?.nuke_unlocked ?? false)
      await adminToggleNukes(unlocked)
      flash(unlocked ? 'Nuclear actions UNLOCKED' : 'Nuclear actions locked', 'success')
      refreshStatus()
    } catch (err) {
      console.error(err)
      flash('Failed to toggle nuclear state.', 'error')
    }
  }

  const injectCrisis = async () => {
    if (!selectedCrisis) { flash('Select a crisis first.', 'error'); return }
    try {
      await adminInjectCrisis(selectedCrisis)
      flash(`Crisis injected.`, 'success')
      setSelectedCrisis('')
      refreshStatus()
    } catch (err) {
      console.error(err)
      flash('Failed to inject crisis.', 'error')
    }
  }

  const clearCrisis = async () => {
    try {
      await adminClearCrisis()
      flash('Active crisis cleared.', 'success')
      refreshStatus()
    } catch (err) {
      console.error(err)
      flash('Failed to clear crisis.', 'error')
    }
  }

  const timerState = timer?.state ?? 'idle'
  const totalEscalation = globalStatus?.total_escalation ?? 0

  return (
    <div className="min-h-screen bg-warroom-blue px-6 py-8 text-slate-100">
      {/* Header */}
      <div className="mx-auto max-w-6xl">
        <div className="flex items-center justify-between border-b border-slate-700 pb-4">
          <div>
            <h1 className="font-pixel text-2xl tracking-wide text-warroom-cyan">GAME MASTER</h1>
            <p className="mt-1 text-xs text-slate-400">Manage rounds, crises, and game state</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span>{playerCount} player{playerCount !== 1 ? 's' : ''} registered</span>
            <span className={`rounded px-2 py-1 font-semibold uppercase tracking-widest ${
              timerState === 'running' ? 'bg-green-900/40 text-green-400' :
              timerState === 'paused' ? 'bg-warroom-amber/20 text-warroom-amber' :
              'bg-slate-800 text-slate-400'
            }`}>{timerState}</span>
          </div>
        </div>

        {/* Flash message */}
        {message && (
          <div className={`mt-4 rounded border px-4 py-2 text-sm ${
            messageType === 'error' ? 'border-red-500/50 bg-red-900/40 text-red-300' :
            messageType === 'success' ? 'border-green-500/50 bg-green-900/40 text-green-300' :
            'border-warroom-cyan/50 bg-slate-800/60 text-warroom-cyan'
          }`}>{message}</div>
        )}

        {/* ── Quick Status Bar ─────────────────────────────────────────── */}
        <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded border border-slate-700 bg-slate-900/60 p-3 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-400">Round</p>
            <p className="font-pixel text-lg text-warroom-cyan">{currentRound ?? '—'} <span className="text-xs text-slate-500">/ {rounds.length}</span></p>
          </div>
          <div className="rounded border border-slate-700 bg-slate-900/60 p-3 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-400">Players</p>
            <p className="font-pixel text-lg text-warroom-cyan">{playerCount}</p>
          </div>
          <div className="rounded border border-slate-700 bg-slate-900/60 p-3 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-400">Escalation</p>
            <p className={`font-pixel text-lg ${totalEscalation >= 60 ? 'text-red-400' : totalEscalation >= 30 ? 'text-warroom-amber' : 'text-warroom-cyan'}`}>{totalEscalation}</p>
          </div>
          <div className="rounded border border-slate-700 bg-slate-900/60 p-3 text-center">
            <p className="text-xs uppercase tracking-widest text-slate-400">Nukes</p>
            <p className={`font-pixel text-lg ${globalStatus?.nuke_unlocked ? 'text-red-400' : 'text-slate-500'}`}>
              {globalStatus?.nuke_unlocked ? 'UNLOCKED' : 'LOCKED'}
            </p>
          </div>
        </div>

        {/* ── Round Controls ───────────────────────────────────────────── */}
        <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Round Controls</h2>
          <div className="mt-3 flex flex-wrap gap-3">
            <button className="rounded border border-green-500/50 bg-green-900/30 px-5 py-2 text-sm font-semibold text-green-300 hover:bg-green-900/50" onClick={() => call('start')}>
              Start Round
            </button>
            <button className="rounded border border-warroom-cyan/50 bg-warroom-cyan/20 px-5 py-2 text-sm font-semibold text-warroom-cyan hover:bg-warroom-cyan/30" onClick={() => call('advance')}>
              Resolve & Advance
            </button>
            {timerState === 'running' ? (
              <button className="rounded border border-warroom-amber/50 bg-warroom-amber/20 px-5 py-2 text-sm font-semibold text-warroom-amber hover:bg-warroom-amber/30" onClick={() => call('pause')}>
                Pause Timer
              </button>
            ) : timerState === 'paused' ? (
              <button className="rounded border border-green-500/50 bg-green-900/20 px-5 py-2 text-sm font-semibold text-green-300 hover:bg-green-900/30" onClick={() => call('resume')}>
                Resume Timer
              </button>
            ) : null}
          </div>
        </div>

        {/* ── Teams ────────────────────────────────────────────────────── */}
        {teams.length > 0 && (
          <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">Teams</h2>
            <div className="mt-3 grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {teams.map((t) => (
                <div key={t.id} className="rounded border border-slate-700/60 bg-warroom-blue/30 px-3 py-2 text-xs">
                  <span className="font-semibold text-slate-200">{t.nation_name}</span>
                  <span className="ml-2 text-slate-500">{t.nation_code}</span>
                  <span className={`ml-auto float-right ${t.members >= t.seat_cap ? 'text-warroom-amber' : 'text-slate-400'}`}>
                    {t.members}/{t.seat_cap}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Rounds Overview ──────────────────────────────────────────── */}
        {rounds.length > 0 && (
          <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">Rounds</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {rounds.map((r) => (
                <div
                  key={r.round_number}
                  className={`rounded border px-3 py-1 text-xs font-semibold ${
                    r.status === 'active' ? 'border-green-500/60 bg-green-900/30 text-green-300' :
                    r.status === 'resolved' ? 'border-slate-600 bg-slate-800 text-slate-400' :
                    'border-slate-700 bg-slate-900/40 text-slate-500'
                  }`}
                >
                  R{r.round_number}: {r.status}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {/* ── Nuclear Controls ──────────────────────────────────────── */}
          <div className="rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">Nuclear Controls</h2>
            <p className="mt-2 text-sm text-slate-300">Current state: <span className={globalStatus?.nuke_unlocked ? 'font-semibold text-red-400' : 'text-slate-400'}>{globalStatus?.nuke_unlocked ? 'UNLOCKED' : 'Locked'}</span></p>
            <button className="mt-3 w-full rounded border border-warroom-amber/50 bg-warroom-amber/20 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/30" onClick={toggleNukes}>
              {globalStatus?.nuke_unlocked ? 'Lock Nuclear Options' : 'Unlock Nuclear Options'}
            </button>
            {globalStatus?.doom_triggered && <p className="mt-3 text-xs text-red-400">GAME OVER: {globalStatus.doom_message}</p>}
          </div>

          {/* ── Crisis Injection ──────────────────────────────────────── */}
          <div className="rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">Crisis Injection</h2>
            <select className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-sm" value={selectedCrisis} onChange={(e) => setSelectedCrisis(e.target.value)}>
              <option value="">Select crisis</option>
              {availableCrises.map((crisis) => (
                <option key={crisis.code} value={crisis.code}>{crisis.title}</option>
              ))}
            </select>
            <div className="mt-3 flex gap-2">
              <button className="flex-1 rounded border border-warroom-cyan/50 bg-warroom-cyan/20 px-3 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-cyan hover:bg-warroom-cyan/30" onClick={injectCrisis}>
                Inject Crisis
              </button>
              <button className="flex-1 rounded border border-slate-600 bg-slate-800 px-3 py-2 text-xs uppercase tracking-widest text-slate-300 hover:bg-slate-700" onClick={clearCrisis}>
                Clear Crisis
              </button>
            </div>
            {globalStatus?.active_crisis && (
              <div className="mt-3 rounded border border-warroom-amber/50 bg-warroom-amber/10 p-3 text-xs text-warroom-amber">
                <p className="font-semibold uppercase tracking-widest">Active Crisis</p>
                <p className="text-sm">{globalStatus.active_crisis.title}</p>
                <p>{globalStatus.active_crisis.summary}</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Crisis Log ───────────────────────────────────────────────── */}
        {crisisHistory.length > 0 && (
          <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">Crisis Log</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {crisisHistory.map((item) => (
                <li key={`${item.code}-${item.applied_at}`} className="rounded border border-slate-700/60 p-3">
                  <p className="text-warroom-amber">{item.title}</p>
                  <p className="text-xs text-slate-400">{item.applied_at}</p>
                  <p className="text-xs">{item.summary}</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Proposal Oversight ───────────────────────────────────────── */}
        {proposalPreview && (
          <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">Proposal Oversight</h2>
            <p className="text-xs text-slate-400">Vetoes used: {proposalPreview.vetoes_used}/{proposalPreview.limit}</p>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {proposalPreview.teams.map((team: ProposalPreview) => (
                <div key={team.team_id} className="rounded border border-slate-700/60 bg-warroom-blue/20 p-3 text-xs text-slate-300">
                  <p className="text-xs uppercase text-slate-400">{team.nation_name}</p>
                  <div className="mt-2 space-y-2">
                    {team.proposals.map((proposal) => (
                      <div key={proposal.id} className="rounded border border-slate-700/60 bg-slate-900/40 p-2">
                        <p>Slot {proposal.slot}: {proposal.action_code} ({proposal.status}) — votes {proposal.votes}</p>
                        {proposal.status === 'draft' && (
                          <button className="mt-1 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1 text-[10px] uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/20" onClick={() => gmVetoProposal(proposal.id)}>
                            Veto
                          </button>
                        )}
                        {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Already vetoed</p>}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Reset Zone ───────────────────────────────────────────────── */}
        <div className="mt-8 rounded border border-red-900/50 bg-red-950/20 p-4">
          <h2 className="font-pixel text-sm text-red-400">Reset Zone</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <div>
              <p className="text-xs text-slate-400">Reset game state only (keeps player accounts, wipes rounds/proposals/scores).</p>
              <button className="mt-2 w-full rounded border border-warroom-amber/50 bg-warroom-amber/10 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/20" onClick={() => call('reset')}>
                Reset Game
              </button>
            </div>
            <div>
              <p className="text-xs text-slate-400">Full reset — wipe everything including all player accounts. Fresh start for new players.</p>
              {!confirmFullReset ? (
                <button className="mt-2 w-full rounded border border-red-500/50 bg-red-900/20 py-2 text-xs font-semibold uppercase tracking-widest text-red-400 hover:bg-red-900/30" onClick={() => setConfirmFullReset(true)}>
                  Full Reset
                </button>
              ) : (
                <div className="mt-2 flex gap-2">
                  <button className="flex-1 rounded border border-red-500 bg-red-900/40 py-2 text-xs font-bold uppercase tracking-widest text-red-300 hover:bg-red-900/60" onClick={handleFullReset}>
                    Confirm Full Reset
                  </button>
                  <button className="flex-1 rounded border border-slate-600 bg-slate-800 py-2 text-xs uppercase tracking-widest text-slate-300 hover:bg-slate-700" onClick={() => setConfirmFullReset(false)}>
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <p className="mt-8 text-center text-xs text-slate-600">Game Master Panel — Cyber War Simulation</p>
      </div>
    </div>
  )
}

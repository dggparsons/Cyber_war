import { useState, useCallback, useEffect } from 'react'
import {
  adminAdvanceRound,
  adminListRounds,
  adminResetRounds,
  adminStartRound,
  adminPauseTimer,
  adminResumeTimer,
  adminFetchStatus,
  adminToggleNukes,
  adminInjectCrisis,
  adminClearCrisis,
  vetoProposal,
  type GlobalStatePayload,
  type CrisisInfo,
  type ProposalPreview,
} from '../lib/api'
import { DEFAULT_GLOBAL_STATE } from '../lib/gameUtils'

export function AdminPanel() {
  const [message, setMessage] = useState<string | null>(null)
  const [rounds, setRounds] = useState<any[]>([])
  const [globalStatus, setGlobalStatus] = useState<GlobalStatePayload | null>(null)
  const [crisisHistory, setCrisisHistory] = useState<CrisisInfo[]>([])
  const [availableCrises, setAvailableCrises] = useState<CrisisInfo[]>([])
  const [selectedCrisis, setSelectedCrisis] = useState('')
  const [proposalPreview, setProposalPreview] = useState<any | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const data = await adminFetchStatus()
      setGlobalStatus(data.global ?? DEFAULT_GLOBAL_STATE)
      setCrisisHistory(data.crises ?? [])
      setAvailableCrises(data.available_crises ?? [])
      setProposalPreview(data.proposal_preview ?? null)
    } catch (err) {
      console.error(err)
      setMessage('Failed to fetch GM status — ensure you are authenticated.')
    }
  }, [])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  const call = async (action: 'start' | 'advance' | 'reset' | 'list' | 'pause' | 'resume') => {
    try {
      setMessage('Working…')
      if (action === 'start') {
        await adminStartRound()
        setMessage('Round started')
      } else if (action === 'advance') {
        await adminAdvanceRound()
        setMessage('Round resolved and advanced')
      } else if (action === 'reset') {
        await adminResetRounds()
        setMessage('Rounds reset')
      } else if (action === 'pause') {
        await adminPauseTimer()
        setMessage('Timer paused')
      } else if (action === 'resume') {
        await adminResumeTimer()
        setMessage('Timer resumed')
      } else {
        const data = await adminListRounds()
        setRounds(data)
        setMessage('Fetched round status')
      }
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Admin action failed — ensure you are logged in as GM.')
    }
  }

  const gmVetoProposal = async (proposalId: number) => {
    try {
      await vetoProposal(proposalId)
      setMessage('Veto issued')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Veto failed — proposal may already be locked.')
    }
  }

  const toggleNukes = async () => {
    try {
      const unlocked = !(globalStatus?.nuke_unlocked ?? false)
      await adminToggleNukes(unlocked)
      setMessage(unlocked ? 'Nuclear actions unlocked' : 'Nuclear actions locked')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Failed to toggle nuclear state.')
    }
  }

  const injectCrisis = async () => {
    if (!selectedCrisis) {
      setMessage('Select a crisis before injecting.')
      return
    }
    try {
      await adminInjectCrisis(selectedCrisis)
      setMessage(`Crisis ${selectedCrisis} injected.`)
      setSelectedCrisis('')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Failed to inject crisis.')
    }
  }

  const clearCrisis = async () => {
    try {
      await adminClearCrisis()
      setMessage('Active crisis cleared.')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Failed to clear crisis.')
    }
  }

  return (
    <div className="min-h-screen bg-warroom-blue px-6 py-8 text-slate-100">
      <h1 className="font-pixel text-xl text-warroom-cyan">GM Control Panel</h1>
      <div className="mt-4 flex flex-wrap gap-3">
        <button className="rounded border border-slate-600 bg-warroom-amber/40 px-4 py-2 text-sm" onClick={() => call('start')}>Start Round</button>
        <button className="rounded border border-slate-600 bg-warroom-cyan/30 px-4 py-2 text-sm" onClick={() => call('advance')}>Resolve & Advance</button>
        <button className="rounded border border-slate-600 bg-slate-700 px-4 py-2 text-sm" onClick={() => call('reset')}>Reset Rounds</button>
        <button className="rounded border border-slate-600 bg-slate-700 px-4 py-2 text-sm" onClick={() => call('list')}>List Rounds</button>
        <button className="rounded border border-slate-600 bg-warroom-amber/30 px-4 py-2 text-sm" onClick={() => call('pause')}>Pause Timer</button>
        <button className="rounded border border-slate-600 bg-warroom-cyan/30 px-4 py-2 text-sm" onClick={() => call('resume')}>Resume Timer</button>
      </div>
      {message && <p className="mt-4 text-sm text-slate-300">{message}</p>}
      {rounds.length > 0 && (
        <div className="mt-6 space-y-2">
          {rounds.map((round: any) => (
            <div key={round.id} className="rounded border border-slate-700 bg-slate-900/60 p-3 text-sm">
              Round {round.round_number}: {round.status} (start: {round.started_at ?? '—'})
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Nuclear Controls</h2>
          <p className="mt-2 text-sm text-slate-300">Current state: {globalStatus?.nuke_unlocked ? 'Unlocked' : 'Locked'}</p>
          <button className="mt-3 w-full rounded border border-warroom-amber/50 bg-warroom-amber/20 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-amber" onClick={toggleNukes}>
            {globalStatus?.nuke_unlocked ? 'Lock Nuclear Options' : 'Unlock Nuclear Options'}
          </button>
          {globalStatus?.doom_triggered && <p className="mt-3 text-xs text-warroom-amber">Game-over state active: {globalStatus.doom_message}</p>}
        </div>
        <div className="rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Crisis Injection</h2>
          <select className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-sm" value={selectedCrisis} onChange={(e) => setSelectedCrisis(e.target.value)}>
            <option value="">Select crisis</option>
            {availableCrises.map((crisis) => (
              <option key={crisis.code} value={crisis.code}>
                {crisis.title}
              </option>
            ))}
          </select>
          <div className="mt-3 flex gap-2">
            <button className="flex-1 rounded border border-warroom-cyan/50 bg-warroom-cyan/20 px-3 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-cyan" onClick={injectCrisis}>
              Inject Crisis
            </button>
            <button className="flex-1 rounded border border-slate-600 bg-slate-800 px-3 py-2 text-xs uppercase tracking-widest text-slate-300" onClick={clearCrisis}>
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
                      <p>
                        Slot {proposal.slot}: {proposal.action_code} ({proposal.status}) — votes {proposal.votes}
                      </p>
                      {proposal.status === 'draft' && (
                        <button className="mt-1 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1 text-[10px] uppercase tracking-widest text-warroom-amber" onClick={() => gmVetoProposal(proposal.id)}>
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
    </div>
  )
}

import type { ActionDefinition, CrisisInfo } from '../lib/api'
import type { Proposal } from '../lib/gameUtils'
import { getCategoryColor } from '../lib/gameUtils'
import { ActiveCrisisBanner } from './overlays'

type TeamOption = { team_id: number; nation_name: string }

type Props = {
  nukeUnlocked: boolean
  doomActive: boolean
  activeCrisis: CrisisInfo | null
  availableActions: ActionDefinition[]
  actions: ActionDefinition[]
  activeProposals: Proposal[]
  selection: Record<number, string>
  targets: Record<number, number>
  teamOptions: TeamOption[]
  falseFlagCount: number
  falseFlagTargets: Record<number, number | ''>
  isCaptain: boolean
  onSelectionChange: (slot: number, value: string) => void
  onTargetChange: (slot: number, value: number) => void
  onSubmitProposal: (slot: number) => void
  onVote: (proposalId: number, value: 1 | -1) => void
  onApplyFalseFlag: (proposalId: number) => void
  onFalseFlagTargetChange: (proposalId: number, value: number | '') => void
  onCaptainOverride?: (proposalId: number) => void
}

export function ActionConsole({
  nukeUnlocked, doomActive, activeCrisis, availableActions, actions,
  activeProposals, selection, targets, teamOptions,
  falseFlagCount, falseFlagTargets, isCaptain,
  onSelectionChange, onTargetChange, onSubmitProposal,
  onVote, onApplyFalseFlag, onFalseFlagTargetChange, onCaptainOverride,
}: Props) {
  const actionName = (code: string) => actions.find((a) => a.code === code)?.name ?? code

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10 space-y-4">
      <h2 className="font-pixel text-sm text-warroom-cyan">Action Console</h2>
      {!nukeUnlocked && <p className="text-xs text-warroom-amber">Catastrophic actions are locked until the GM escalates the scenario.</p>}
      {nukeUnlocked && <p className="text-xs text-warroom-amber">☢ Nuclear options are live. Any successful strike ends the game immediately.</p>}
      {activeCrisis && <ActiveCrisisBanner crisis={activeCrisis} />}
      {doomActive && <p className="text-xs text-warroom-amber">Game over state detected — inputs frozen.</p>}
      <div className="rounded-lg border border-slate-700/70 bg-warroom-slate/60 p-4">
        <p className="text-xs uppercase tracking-wider text-slate-400 mb-3">Propose an Action</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-3">
          <div className="flex-1">
            <select className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm disabled:opacity-50" value={selection[1] ?? ''} onChange={(e) => onSelectionChange(1, e.target.value)} disabled={doomActive}>
              <option value="">Select action</option>
              {availableActions.map((action) => (
                <option key={action.code} value={action.code} style={{ color: getCategoryColor(action.category) }}>{action.name}</option>
              ))}
            </select>
          </div>
          {actions.find((a) => a.code === selection[1])?.target_required && (
            <div className="flex-1">
              <select className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm disabled:opacity-50" value={targets[1] ?? ''} onChange={(e) => onTargetChange(1, parseInt(e.target.value))} disabled={doomActive}>
                <option value="">Select target</option>
                {teamOptions.map((entry) => (
                  <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
                ))}
              </select>
            </div>
          )}
          <button className={`rounded border border-warroom-cyan/60 bg-warroom-cyan/20 px-6 py-2 text-xs font-bold tracking-wide text-warroom-cyan transition hover:bg-warroom-cyan/30 hover:border-warroom-cyan ${doomActive ? 'cursor-not-allowed opacity-50 hover:border-slate-600 hover:bg-warroom-cyan/20' : ''}`} onClick={() => onSubmitProposal(1)} disabled={doomActive}>Submit Proposal</button>
        </div>
      </div>

      {/* Team Proposals */}
      <div>
        <h3 className="font-pixel text-xs text-warroom-cyan">Team Proposals</h3>
        <div className="mt-3 space-y-2">
          {activeProposals.length === 0 && <p className="text-xs text-slate-400">No proposals yet.</p>}
          {activeProposals.map((proposal) => {
            const totalVotes = proposal.votes?.reduce((sum, vote) => sum + vote.value, 0) ?? 0
            const locked = proposal.status === 'locked'
            const closed = proposal.status === 'closed'
            const votingDisabled = locked || closed || doomActive
            return (
              <div key={proposal.id} className="rounded border border-slate-700 bg-warroom-blue/40 px-3 py-2 text-sm text-slate-200">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{actionName(proposal.action_code)}</p>
                    {proposal.target_team_id && <p className="text-xs text-slate-400">Target: {teamOptions.find((t) => t.team_id === proposal.target_team_id)?.nation_name ?? proposal.target_team_id}</p>}
                    {locked && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Locked In</p>}
                    {closed && <p className="text-[10px] uppercase tracking-widest text-slate-400">Closed</p>}
                    {proposal.false_flag_target_team_id && (
                      <p className="text-[10px] uppercase tracking-widest text-warroom-cyan">False flag queued: {teamOptions.find((team) => team.team_id === proposal.false_flag_target_team_id)?.nation_name ?? proposal.false_flag_target_team_id}</p>
                    )}
                    {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Vetoed by Peace Council</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="rounded border border-slate-600 px-2 text-xs disabled:opacity-40" onClick={() => onVote(proposal.id, 1)} disabled={votingDisabled}>▲</button>
                    <span className="text-warroom-amber">{totalVotes}</span>
                    <button className="rounded border border-slate-600 px-2 text-xs disabled:opacity-40" onClick={() => onVote(proposal.id, -1)} disabled={votingDisabled}>▼</button>
                  </div>
                </div>
                {isCaptain && proposal.status === 'draft' && onCaptainOverride && (
                  <button className="mt-1 w-full rounded border border-warroom-cyan/40 bg-warroom-cyan/10 py-1 text-[10px] uppercase tracking-widest text-warroom-cyan" onClick={() => onCaptainOverride(proposal.id)}>Captain Override: Lock</button>
                )}
                {!proposal.false_flag_target_team_id && proposal.status === 'draft' && falseFlagCount > 0 && (
                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <select className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1" value={falseFlagTargets[proposal.id] ?? ''} onChange={(e) => onFalseFlagTargetChange(proposal.id, e.target.value === '' ? '' : Number(e.target.value))}>
                      <option value="">Select blame nation</option>
                      {teamOptions.map((entry) => (
                        <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
                      ))}
                    </select>
                    <button className="rounded border border-warroom-amber/40 bg-warroom-amber/10 px-3 py-1 text-xs uppercase tracking-widest text-warroom-amber" onClick={() => onApplyFalseFlag(proposal.id)}>False Flag</button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

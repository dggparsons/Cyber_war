import { useState } from 'react'
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
  const [lockConfirm, setLockConfirm] = useState<number | null>(null)
  const actionName = (code: string) => actions.find((a) => a.code === code)?.name ?? code

  const selectedAction = actions.find((a) => a.code === selection[1])

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10 space-y-3">
      <h2 className="font-pixel text-sm text-warroom-cyan">Action Console</h2>
      {!nukeUnlocked && <p className="text-xs text-warroom-amber">Catastrophic actions are locked until the GM escalates the scenario.</p>}
      {nukeUnlocked && <p className="text-xs text-warroom-amber">☢ Nuclear options are live. Any successful strike ends the game immediately.</p>}
      {activeCrisis && <ActiveCrisisBanner crisis={activeCrisis} />}
      {doomActive && <p className="text-xs text-warroom-amber">Game over state detected — inputs frozen.</p>}

      {/* Full-width heading */}
      <p className="text-xs uppercase tracking-wider text-slate-400">Propose an Action</p>

      {/* Two-column layout: form left, proposals right */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* LEFT: Action selection form */}
        <div className="space-y-2">
          <select
            className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm disabled:opacity-50"
            value={selection[1] ?? ''}
            onChange={(e) => onSelectionChange(1, e.target.value)}
            disabled={doomActive}
          >
            <option value="">Select action</option>
            {availableActions.map((action) => (
              <option key={action.code} value={action.code} style={{ color: getCategoryColor(action.category) }}>{action.name}</option>
            ))}
          </select>

          {selectedAction?.target_required && (
            <select
              className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm disabled:opacity-50"
              value={targets[1] ?? ''}
              onChange={(e) => onTargetChange(1, parseInt(e.target.value))}
              disabled={doomActive}
            >
              <option value="">Select target</option>
              {teamOptions.map((entry) => (
                <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
              ))}
            </select>
          )}

          <button
            className={`w-full rounded border border-warroom-cyan/60 bg-warroom-cyan/20 px-6 py-2 text-xs font-bold tracking-wide text-warroom-cyan transition hover:bg-warroom-cyan/30 hover:border-warroom-cyan ${doomActive ? 'cursor-not-allowed opacity-50' : ''}`}
            onClick={() => onSubmitProposal(1)}
            disabled={doomActive}
          >
            Submit Proposal
          </button>

          {/* Action description preview */}
          {selectedAction && (
            <div className="rounded border border-slate-700/50 bg-warroom-blue/30 px-3 py-2 text-xs text-slate-300">
              <p>{selectedAction.description}</p>
              <p className="mt-1">
                <span className="text-slate-400">Category:</span>{' '}
                <span style={{ color: getCategoryColor(selectedAction.category) }}>{selectedAction.category.replace('_', ' ')}</span>
                <span className="ml-3 text-slate-400">Escalation:</span>{' '}
                <span className={selectedAction.escalation >= 20 ? 'text-red-400' : selectedAction.escalation >= 5 ? 'text-warroom-amber' : 'text-green-400'}>+{selectedAction.escalation}</span>
                {selectedAction.visibility === 'covert' && (
                  <span className="ml-3 rounded border border-warroom-cyan/40 bg-warroom-cyan/10 px-1.5 py-0.5 text-[10px] uppercase tracking-widest text-warroom-cyan" title="Your identity stays hidden unless the target's security detects you">COVERT</span>
                )}
              </p>
            </div>
          )}
        </div>

        {/* RIGHT: Team Proposals */}
        <div>
          <h3 className="font-pixel text-xs text-warroom-cyan mb-2">Team Proposals</h3>
          <div className="space-y-2">
            {activeProposals.length === 0 && <p className="text-xs text-slate-400">No proposals yet.</p>}
            {activeProposals.map((proposal) => {
              const totalVotes = proposal.votes?.reduce((sum, vote) => sum + vote.value, 0) ?? 0
              const locked = proposal.status === 'locked'
              const closed = proposal.status === 'closed'
              const votingDisabled = locked || closed || doomActive
              return (
                <div key={proposal.id} className="rounded border border-slate-700 bg-warroom-blue/40 px-3 py-2 text-sm text-slate-200">
                  <div className="flex items-center justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold truncate">{actionName(proposal.action_code)}</p>
                      {proposal.target_team_id && <p className="text-xs text-slate-400">Target: {teamOptions.find((t) => t.team_id === proposal.target_team_id)?.nation_name ?? proposal.target_team_id}</p>}
                      {locked && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Locked In</p>}
                      {closed && <p className="text-[10px] uppercase tracking-widest text-slate-400">Closed</p>}
                      {proposal.false_flag_target_team_id && (
                        <p className="text-[10px] uppercase tracking-widest text-warroom-cyan">False flag: {teamOptions.find((team) => team.team_id === proposal.false_flag_target_team_id)?.nation_name ?? proposal.false_flag_target_team_id}</p>
                      )}
                      {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Vetoed by Peace Council</p>}
                    </div>
                    <div className="flex items-center gap-1.5 ml-2">
                      <button className="rounded border border-slate-600 px-1.5 text-xs disabled:opacity-40" onClick={() => onVote(proposal.id, 1)} disabled={votingDisabled}>▲</button>
                      <span className="text-warroom-amber min-w-[1.25rem] text-center">{totalVotes}</span>
                      <button className="rounded border border-slate-600 px-1.5 text-xs disabled:opacity-40" onClick={() => onVote(proposal.id, -1)} disabled={votingDisabled}>▼</button>
                    </div>
                  </div>
                  {isCaptain && proposal.status === 'draft' && onCaptainOverride && (
                    lockConfirm === proposal.id ? (
                      <div className="mt-1 flex gap-2">
                        <button className="flex-1 rounded border border-warroom-amber/60 bg-warroom-amber/20 py-1 text-[10px] font-bold uppercase tracking-widest text-warroom-amber" onClick={() => { onCaptainOverride(proposal.id); setLockConfirm(null) }}>Confirm Lock</button>
                        <button className="flex-1 rounded border border-slate-600 bg-slate-800 py-1 text-[10px] uppercase tracking-widest text-slate-300" onClick={() => setLockConfirm(null)}>Cancel</button>
                      </div>
                    ) : (
                      <button className="mt-1 w-full rounded border border-warroom-cyan/40 bg-warroom-cyan/10 py-1 text-[10px] uppercase tracking-widest text-warroom-cyan" onClick={() => setLockConfirm(proposal.id)}>Captain Override: Lock</button>
                    )
                  )}
                  {!proposal.false_flag_target_team_id && proposal.status === 'draft' && falseFlagCount > 0 && (
                    <div className="mt-2 flex items-center gap-2 text-xs">
                      <select className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1" value={falseFlagTargets[proposal.id] ?? ''} onChange={(e) => onFalseFlagTargetChange(proposal.id, e.target.value === '' ? '' : Number(e.target.value))}>
                        <option value="">Blame nation</option>
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
      </div>
    </section>
  )
}

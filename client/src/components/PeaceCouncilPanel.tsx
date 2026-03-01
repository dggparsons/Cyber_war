import type { ProposalPreview } from '../lib/api'

type Props = {
  previewData: { round: number; limit: number; vetoes_used: number; teams: ProposalPreview[] }
  onVetoProposal: (proposalId: number) => void
}

export function PeaceCouncilPanel({ previewData, onVetoProposal }: Props) {
  const vetoLimitReached = previewData.vetoes_used >= previewData.limit

  return (
    <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4 text-sm text-slate-200">
      <div className="flex items-center justify-between">
        <h3 className="font-pixel text-xs text-warroom-cyan">Peace Council Oversight</h3>
        <p className="text-[10px] uppercase tracking-widest text-slate-400">Vetoes {previewData.vetoes_used}/{previewData.limit}</p>
      </div>
      <div className="mt-3 space-y-3 max-h-56 overflow-y-auto">
        {previewData.teams.map((team) => (
          <div key={team.team_id} className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2">
            <p className="text-xs uppercase text-slate-400">{team.nation_name}</p>
            {team.proposals.map((proposal) => (
              <div key={proposal.id} className="mt-1 rounded border border-slate-700/50 bg-slate-900/40 p-2 text-xs">
                <p>Slot {proposal.slot}: {proposal.action_code} ({proposal.status}) — votes {proposal.votes}</p>
                {proposal.status === 'draft' && !vetoLimitReached && (
                  <button className="mt-1 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1 text-[10px] uppercase tracking-widest text-warroom-amber" onClick={() => onVetoProposal(proposal.id)}>Veto Proposal</button>
                )}
                {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Vetoed</p>}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

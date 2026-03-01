import type { MegaChallengeData } from '../lib/api'
import type { IntelDropItem } from './modals'

type Props = {
  intelDrops: Array<{ id: number; title: string; description: string; reward: string; status: string }>
  megaChallenge: MegaChallengeData | null
  onSelectIntel: (intel: IntelDropItem) => void
  onOpenMega: () => void
}

export function IntelPanel({ intelDrops, megaChallenge, onSelectIntel, onOpenMega }: Props) {
  return (
    <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4">
      <h3 className="font-pixel text-xs text-warroom-cyan">Intel Drops</h3>
      <div className="mt-3 space-y-2 text-sm text-slate-300">
        {intelDrops.length === 0 && <p className="text-xs text-slate-500">No intel drops yet this round.</p>}
        {intelDrops.map((intel) => (
          <div key={intel.id} className="rounded border border-slate-700/60 p-3 hack-pulse cursor-pointer hover:border-warroom-cyan/40 transition-colors" onClick={() => onSelectIntel(intel)}>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-100">{intel.title}</span>
              <span className={`text-xs uppercase ${intel.status === 'solved' ? 'text-emerald-400' : 'text-warroom-amber'}`}>{intel.status}</span>
            </div>
            <p className="mt-1 text-xs text-slate-400 line-clamp-2">{intel.description}</p>
            <p className="mt-2 text-xs text-warroom-cyan">Reward: {intel.reward}</p>
          </div>
        ))}
        {megaChallenge?.active && (
          <div className="rounded border border-purple-500/50 p-3 hack-pulse cursor-pointer hover:border-purple-400/60 transition-colors" onClick={onOpenMega}>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-purple-400">Mega Challenge</span>
              <span className={`text-xs uppercase ${megaChallenge.already_solved ? 'text-emerald-400' : 'text-purple-400'}`}>
                {megaChallenge.already_solved ? 'solved' : 'active'}
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-400">Multi-stage challenge — click to open</p>
            <p className="mt-2 text-xs text-purple-400">Rewards: {(megaChallenge.reward_tiers ?? [15, 10, 5]).map((r, i) => `${['1st', '2nd', '3rd'][i] ?? `${i + 1}th`} +${r}`).join(' | ')} Influence</p>
          </div>
        )}
      </div>
    </div>
  )
}

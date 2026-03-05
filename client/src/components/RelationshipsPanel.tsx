import type { LeaderboardResponse } from '../lib/api'

type Props = {
  briefingAllies: string[]
  briefingThreats: string[]
  alliances: Array<{ team_a_id: number; team_b_id: number; status: string; formed_at: string | null }>
  teamId: number
  leaderboard: LeaderboardResponse | null
}

export function RelationshipsPanel({ briefingAllies, briefingThreats, alliances, teamId, leaderboard }: Props) {
  const resolveNation = (tid: number) =>
    leaderboard?.entries.find((e) => e.team_id === tid)?.nation_name ?? 'Unknown'

  const activeAlliances = alliances.filter((a) => a.status === 'active')
  const alliancePartners = activeAlliances.map((a) =>
    a.team_a_id === teamId ? resolveNation(a.team_b_id) : resolveNation(a.team_a_id)
  )

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10 text-sm text-slate-200">
      <h2 className="font-pixel text-sm text-warroom-cyan">Relationships</h2>

      {/* Active alliances (formed during game) */}
      {alliancePartners.length > 0 && (
        <div className="mt-3">
          <p className="text-[10px] uppercase tracking-widest text-emerald-400/80 font-semibold mb-1.5">Active Alliances</p>
          <div className="space-y-1">
            {alliancePartners.map((name, i) => (
              <div key={i} className="flex items-center gap-2 rounded border border-emerald-500/30 bg-emerald-900/15 px-2.5 py-1.5">
                <span className="text-emerald-400 text-xs">&#x2694;</span>
                <span className="text-xs text-emerald-300 font-semibold">{name}</span>
                <span className="ml-auto text-[9px] uppercase tracking-widest text-emerald-500/70">Allied</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategic allies (from briefing) */}
      {briefingAllies.length > 0 && (
        <div className="mt-3">
          <p className="text-[10px] uppercase tracking-widest text-warroom-cyan/80 font-semibold mb-1.5">Strategic Allies</p>
          <div className="space-y-1">
            {briefingAllies.map((ally, i) => {
              const [name, ...rest] = ally.split(' — ')
              const detail = rest.join(' — ')
              return (
                <div key={i} className="rounded border border-slate-700/60 bg-warroom-blue/30 px-2.5 py-1.5">
                  <p className="text-xs text-warroom-cyan font-semibold">{name}</p>
                  {detail && <p className="text-[10px] text-slate-500 mt-0.5">{detail}</p>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Threats / enemies (from briefing) */}
      {briefingThreats.length > 0 && (
        <div className="mt-3">
          <p className="text-[10px] uppercase tracking-widest text-red-400/80 font-semibold mb-1.5">Known Threats</p>
          <div className="space-y-1">
            {briefingThreats.map((threat, i) => {
              const [name, ...rest] = threat.split(' — ')
              const detail = rest.join(' — ')
              return (
                <div key={i} className="rounded border border-red-500/20 bg-red-900/10 px-2.5 py-1.5">
                  <p className="text-xs text-red-400 font-semibold">{name}</p>
                  {detail && <p className="text-[10px] text-slate-500 mt-0.5">{detail}</p>}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {alliancePartners.length === 0 && briefingAllies.length === 0 && briefingThreats.length === 0 && (
        <p className="mt-2 text-xs text-slate-500 italic">No known relationships yet.</p>
      )}
    </section>
  )
}

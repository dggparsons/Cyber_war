import type { GameState } from '../lib/gameUtils'

export function BriefingModal({ briefing, onClose }: { briefing: GameState['briefing']; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-warroom-cyan/40 bg-slate-900/90 p-6 shadow-2xl shadow-warroom-cyan/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-warroom-cyan">{briefing.title}</h2>
          <button className="text-xs uppercase text-slate-400 hover:text-warroom-cyan" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-200">{briefing.summary}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded border border-slate-700 p-3">
            <p className="font-semibold text-warroom-amber">Allies</p>
            <ul className="mt-2 list-disc pl-4 text-sm text-slate-300">
              {briefing.allies.map((ally, idx) => (
                <li key={idx}>{ally}</li>
              ))}
            </ul>
          </div>
          <div className="rounded border border-slate-700 p-3">
            <p className="font-semibold text-warroom-amber">Threats</p>
            <ul className="mt-2 list-disc pl-4 text-sm text-slate-300">
              {briefing.threats.map((threat, idx) => (
                <li key={idx}>{threat}</li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-4 rounded border border-slate-700 p-3">
          <p className="font-semibold text-warroom-amber">Consequences</p>
          <p className="mt-2 text-sm text-slate-300">{briefing.consequences}</p>
        </div>
      </div>
    </div>
  )
}

export function NationsModal({ myTeamId, entries, alliances, diplomacyChannels, onClose }: {
  myTeamId: number
  entries: Array<{ team_id: number; nation_name: string; score: number; delta_from_baseline: number; escalation: number }>
  alliances: Array<{ team_a_id: number; team_b_id: number; status: string; formed_at: string | null }>
  diplomacyChannels: any[]
  onClose: () => void
}) {
  const alliedIds = new Set(
    alliances.map((a) => (a.team_a_id === myTeamId ? a.team_b_id : a.team_a_id))
  )
  const diplomacyIds = new Set(
    diplomacyChannels.map((ch: any) => ch.with_team?.id ?? ch.target_team_id).filter(Boolean)
  )

  const getRelationship = (teamId: number) => {
    if (teamId === myTeamId) return 'you'
    if (alliedIds.has(teamId)) return 'allied'
    if (diplomacyIds.has(teamId)) return 'diplomatic'
    return 'neutral'
  }

  const relationshipLabel = (rel: string) => {
    switch (rel) {
      case 'you': return { text: 'YOU', color: 'text-warroom-cyan' }
      case 'allied': return { text: 'ALLIED', color: 'text-emerald-400' }
      case 'diplomatic': return { text: 'IN CONTACT', color: 'text-warroom-amber' }
      default: return { text: 'NEUTRAL', color: 'text-slate-500' }
    }
  }

  const sorted = [...entries].sort((a, b) => b.score - a.score)
  const myEntry = entries.find((e) => e.team_id === myTeamId)
  const myRank = sorted.findIndex((e) => e.team_id === myTeamId) + 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg border border-warroom-amber/40 bg-slate-900/95 p-6 shadow-2xl shadow-warroom-amber/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-warroom-amber">Nations Intel</h2>
          <button className="text-xs uppercase text-slate-400 hover:text-warroom-amber" onClick={onClose}>Close</button>
        </div>
        {myEntry && (
          <div className="mt-3 rounded border border-warroom-cyan/40 bg-warroom-cyan/5 p-3 text-sm">
            <p className="text-xs uppercase tracking-widest text-slate-400">Your Standing</p>
            <p className="text-warroom-cyan font-semibold">{myEntry.nation_name} — Rank #{myRank} of {entries.length}</p>
            <p className="text-xs text-slate-400">Score: {myEntry.score} (delta {myEntry.delta_from_baseline >= 0 ? '+' : ''}{myEntry.delta_from_baseline}) | Escalation: {myEntry.escalation}</p>
          </div>
        )}
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {sorted.map((entry, idx) => {
            const rel = getRelationship(entry.team_id)
            const label = relationshipLabel(rel)
            const isMe = entry.team_id === myTeamId
            return (
              <div key={entry.team_id} className={`rounded border p-3 ${isMe ? 'border-warroom-cyan/50 bg-warroom-cyan/5' : 'border-slate-700/70 bg-warroom-blue/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-warroom-amber font-pixel text-xs">#{idx + 1}</span>
                    <span className={`font-semibold ${isMe ? 'text-warroom-cyan' : 'text-slate-100'}`}>{entry.nation_name}</span>
                  </div>
                  <span className={`text-[10px] uppercase tracking-widest font-semibold ${label.color}`}>{label.text}</span>
                </div>
                <div className="mt-2 flex gap-4 text-xs text-slate-400">
                  <span>Score: <span className="text-slate-200">{entry.score}</span></span>
                  <span>Delta: <span className={entry.delta_from_baseline >= 0 ? 'text-emerald-400' : 'text-red-400'}>{entry.delta_from_baseline >= 0 ? '+' : ''}{entry.delta_from_baseline}</span></span>
                  <span>Escalation: <span className={entry.escalation > 20 ? 'text-red-400' : entry.escalation > 10 ? 'text-warroom-amber' : 'text-slate-200'}>{entry.escalation}</span></span>
                </div>
                {rel === 'allied' && <p className="mt-1 text-[10px] uppercase tracking-widest text-emerald-400/70">Active alliance in place</p>}
                {rel === 'diplomatic' && <p className="mt-1 text-[10px] uppercase tracking-widest text-warroom-amber/70">Diplomacy channel open</p>}
              </div>
            )
          })}
        </div>
        <div className="mt-4 flex gap-4 text-[10px] uppercase tracking-widest text-slate-500">
          <span><span className="text-emerald-400">///</span> Allied</span>
          <span><span className="text-warroom-amber">///</span> In Contact</span>
          <span><span className="text-slate-500">///</span> Neutral</span>
        </div>
      </div>
    </div>
  )
}

export function HowToPlayModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-warroom-cyan/40 bg-slate-900/95 p-6 shadow-2xl shadow-warroom-cyan/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-warroom-cyan">How to Play</h2>
          <button className="text-xs uppercase text-slate-400 hover:text-warroom-cyan" onClick={onClose}>Close</button>
        </div>

        <div className="mt-4 space-y-5 text-sm text-slate-300">
          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">The Scenario</h3>
            <p className="mt-1">You are the decision-makers for a nation in an escalating global cyber conflict. Every round, your team picks actions that affect your nation and others. The goal: <span className="text-warroom-cyan font-semibold">protect your interests without triggering a catastrophic escalation that ends the game for everyone.</span></p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Rounds & Timer</h3>
            <p className="mt-1">The game runs in timed rounds. When the timer is running, you can submit and vote on proposals. When it expires, the GM resolves all actions and advances to the next round. You have <span className="text-warroom-cyan">3 action slots</span> per round.</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Action Slots & Proposals</h3>
            <p className="mt-1">Each slot can hold one action. Any team member can propose an action for a slot. The team votes on proposals — the one with the most votes gets locked in when the round resolves.</p>
            <p className="mt-1">If nobody proposes anything for a slot, it defaults to <span className="text-slate-100">WAIT</span> (do nothing).</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Action Categories</h3>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2"><span className="font-semibold" style={{color:'#22c55e'}}>De-escalation</span> — lower tensions, build trust</div>
              <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2"><span className="font-semibold" style={{color:'#f8fafc'}}>Status Quo</span> — wait, observe, do nothing</div>
              <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2"><span className="font-semibold" style={{color:'#eab308'}}>Posturing</span> — intelligence, sanctions, shows of force</div>
              <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2"><span className="font-semibold" style={{color:'#f97316'}}>Non-violent</span> — cyber attacks on infrastructure</div>
              <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2"><span className="font-semibold" style={{color:'#ef4444'}}>Violent</span> — destructive attacks with real damage</div>
              <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2"><span className="font-semibold" style={{color:'#a855f7'}}>Nuclear</span> — game-ending catastrophic strikes</div>
            </div>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Scoring</h3>
            <p className="mt-1">Your <span className="text-warroom-cyan">Outcome Score</span> = Prosperity + Security + Influence - Escalation. Actions you take (and actions taken against you) shift these stats. The leaderboard ranks nations by score.</p>
            <p className="mt-1">The <span className="text-warroom-cyan">Delta</span> shows how much your score has changed from your starting baseline — positive is good, negative means you're worse off.</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Global Escalation & Doom</h3>
            <p className="mt-1">Every aggressive action adds to a global escalation counter shared by all. When it crosses thresholds, warnings flash. If a nuclear action succeeds, <span className="text-red-400 font-semibold">the game ends immediately and everyone loses</span>. Watch the Doomsday Clock.</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Diplomacy & Alliances</h3>
            <p className="mt-1">Open diplomacy channels with other nations to negotiate. Form alliances for mutual benefit, or break them if trust collapses. Check <span className="text-warroom-amber">Nations Intel</span> to see who you're allied with and where everyone stands.</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Intel Drops & Lifelines</h3>
            <p className="mt-1"><span className="text-warroom-cyan">Intel Drops</span> are puzzles from the GM. Solve them to earn lifelines like <span className="text-warroom-amber">False Flags</span> (blame another nation for your action). Lifelines are limited — use them wisely.</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Crises</h3>
            <p className="mt-1">The GM can inject crises that change the rules mid-game. When a crisis hits, everyone sees it. Adapt your strategy or get caught off guard.</p>
          </div>

          <div className="rounded border border-warroom-cyan/30 bg-warroom-cyan/5 p-3">
            <h3 className="font-pixel text-xs text-warroom-cyan">Key Tips</h3>
            <ul className="mt-2 space-y-1 text-xs text-slate-300 list-disc pl-4">
              <li>Coordinate with your team in <span className="text-warroom-cyan">Team Comms</span> before voting</li>
              <li>Aggressive actions raise everyone's escalation — including yours</li>
              <li>Diplomacy costs nothing and can prevent costly conflicts</li>
              <li>Watch what other nations are doing via the news ticker and leaderboard</li>
              <li>The best outcome is one where your nation thrives without ending the world</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

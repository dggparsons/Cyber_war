import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { GameState } from '../lib/gameUtils'
import type { MegaChallengeData, RoundRecap } from '../lib/api'

export type IntelDropItem = { id: number; title: string; description: string; reward: string; status: string }

export function BriefingModal({ briefing, onClose }: { briefing: GameState['briefing']; onClose: () => void }) {
  const hasSections = briefing.sections && briefing.sections.length > 0

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

        {hasSections ? (
          <div className="mt-4 space-y-4">
            {briefing.sections!.map((section, idx) => (
              <div key={idx} className="rounded border border-slate-700 p-3">
                <p className="font-semibold text-warroom-amber">{section.heading}</p>
                <ul className="mt-2 list-disc pl-4 text-sm text-slate-300 space-y-1">
                  {section.items.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <>
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
          </>
        )}
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
            <p className="mt-1">The game runs in timed rounds. When the timer is running, you can submit and vote on proposals. When it expires, the GM resolves all actions and advances to the next round. You have <span className="text-warroom-cyan">1 action slot</span> per round.</p>
          </div>

          <div>
            <h3 className="font-pixel text-xs text-warroom-amber">Actions & Proposals</h3>
            <p className="mt-1">Each round your team picks one action. Any team member can propose an action. The team votes on proposals — the one with the most votes gets locked in when the round resolves.</p>
            <p className="mt-1">If nobody proposes anything, it defaults to <span className="text-slate-100">WAIT</span> (do nothing).</p>
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

export function IntelModal({ intel, answer, onAnswerChange, onSubmit, onClose }: {
  intel: IntelDropItem
  answer: string
  onAnswerChange: (v: string) => void
  onSubmit: () => void
  onClose: () => void
}) {
  const isSolved = intel.status === 'solved'
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-warroom-cyan/40 bg-slate-900/95 p-6 shadow-2xl shadow-warroom-cyan/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-warroom-cyan">{intel.title}</h2>
          <div className="flex items-center gap-3">
            <span className={`text-xs uppercase tracking-widest font-semibold ${isSolved ? 'text-emerald-400' : 'text-warroom-amber'}`}>
              {intel.status}
            </span>
            <button className="text-xs uppercase text-slate-400 hover:text-warroom-cyan" onClick={onClose}>Close</button>
          </div>
        </div>

        <div className="mt-4 rounded border border-slate-700/60 bg-warroom-blue/30 p-4">
          <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Puzzle</p>
          <pre className="whitespace-pre-wrap font-mono text-sm text-slate-200 leading-relaxed">{intel.description}</pre>
        </div>

        <div className="mt-3 flex items-center gap-2 text-sm">
          <span className="text-xs uppercase tracking-widest text-slate-500">Reward:</span>
          <span className="text-warroom-cyan font-semibold">{intel.reward}</span>
        </div>

        {isSolved ? (
          <div className="mt-4 rounded border border-emerald-500/40 bg-emerald-900/20 p-3 text-center">
            <p className="text-emerald-400 font-semibold">Puzzle Solved</p>
            <p className="text-xs text-slate-400 mt-1">Reward has been applied to your team.</p>
          </div>
        ) : (
          <div className="mt-4">
            <label className="text-xs uppercase tracking-widest text-slate-500">Your Answer</label>
            <div className="mt-2 flex gap-2">
              <input
                className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-warroom-cyan/60 focus:outline-none"
                placeholder="Enter solution..."
                value={answer}
                onChange={(e) => onAnswerChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && answer) onSubmit() }}
              />
              <button
                className="rounded border border-warroom-cyan/40 bg-warroom-cyan/10 px-4 py-2 text-xs uppercase tracking-widest text-warroom-cyan hover:bg-warroom-cyan/20"
                onClick={onSubmit}
              >
                Submit
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function MegaChallengeModal({ challenge, answer, onAnswerChange, onSubmit, onClose }: {
  challenge: MegaChallengeData
  answer: string
  onAnswerChange: (v: string) => void
  onSubmit: () => void
  onClose: () => void
}) {
  const tiers = challenge.reward_tiers ?? [15, 10, 5]
  const ordinal = (n: number) => n === 1 ? '1st' : n === 2 ? '2nd' : n === 3 ? '3rd' : `${n}th`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg border border-purple-500/40 bg-slate-900/95 p-6 shadow-2xl shadow-purple-500/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-purple-400">Mega Challenge</h2>
          <button className="text-xs uppercase text-slate-400 hover:text-purple-400" onClick={onClose}>Close</button>
        </div>

        <div className="mt-2 flex gap-3 text-[10px] uppercase tracking-widest text-slate-500">
          {tiers.map((r, i) => (
            <span key={i} className="rounded border border-purple-500/30 bg-purple-900/20 px-2 py-0.5 text-purple-300">
              {ordinal(i + 1)} place: +{r} Influence
            </span>
          ))}
        </div>

        <div className="mt-4 rounded border border-slate-700/60 bg-warroom-blue/30 p-5 mega-markdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              h2: ({ children }) => <h2 className="font-pixel text-base text-red-400 mt-6 mb-3 first:mt-0">{children}</h2>,
              h3: ({ children }) => <h3 className="font-pixel text-sm text-purple-400 mt-5 mb-2 border-b border-slate-700/50 pb-1">{children}</h3>,
              p: ({ children }) => <p className="text-sm text-slate-200 leading-relaxed mb-3">{children}</p>,
              strong: ({ children }) => <strong className="text-warroom-amber font-semibold">{children}</strong>,
              em: ({ children }) => <em className="text-slate-400 italic">{children}</em>,
              code: ({ className, children }) => {
                const isBlock = className?.includes('language-') || String(children).includes('\n')
                return isBlock
                  ? <code className="block bg-black/50 border border-slate-700/60 rounded p-3 my-3 text-xs font-mono text-emerald-300 whitespace-pre overflow-x-auto leading-relaxed">{children}</code>
                  : <code className="bg-black/40 border border-slate-700/40 rounded px-1.5 py-0.5 text-xs font-mono text-emerald-300">{children}</code>
              },
              pre: ({ children }) => <div className="my-2">{children}</div>,
              blockquote: ({ children }) => <blockquote className="border-l-2 border-purple-500/60 pl-4 my-3 text-sm text-slate-300 bg-purple-900/10 py-2 rounded-r">{children}</blockquote>,
              hr: () => <hr className="border-slate-700/50 my-5" />,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 text-sm text-slate-300 mb-3">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 text-sm text-slate-300 mb-3">{children}</ol>,
              table: ({ children }) => <table className="w-full text-sm text-slate-300 my-3 border border-slate-700/50">{children}</table>,
              thead: ({ children }) => <thead className="bg-slate-800/60 text-xs uppercase text-slate-400">{children}</thead>,
              th: ({ children }) => <th className="border border-slate-700/50 px-3 py-1.5 text-left">{children}</th>,
              td: ({ children }) => <td className="border border-slate-700/50 px-3 py-1.5">{children}</td>,
            }}
          >
            {challenge.description}
          </ReactMarkdown>
        </div>

        {challenge.solved_by && challenge.solved_by.length > 0 && (
          <div className="mt-4">
            <p className="text-xs uppercase tracking-widest text-slate-500 mb-2">Solved By</p>
            <div className="flex flex-wrap gap-2">
              {challenge.solved_by.map((s) => (
                <span key={s.team_id} className="rounded border border-emerald-500/30 bg-emerald-900/20 px-3 py-1 text-xs text-emerald-400">
                  #{s.position} — Team {s.team_id} (+{s.reward})
                </span>
              ))}
            </div>
          </div>
        )}

        {challenge.already_solved ? (
          <div className="mt-4 rounded border border-emerald-500/40 bg-emerald-900/20 p-3 text-center">
            <p className="text-emerald-400 font-semibold">Your team has solved this challenge!</p>
          </div>
        ) : (
          <div className="mt-4">
            <label className="text-xs uppercase tracking-widest text-slate-500">Your Answer</label>
            <div className="mt-2 flex gap-2">
              <input
                className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-purple-400/60 focus:outline-none"
                placeholder="Enter solution..."
                value={answer}
                onChange={(e) => onAnswerChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && answer) onSubmit() }}
              />
              <button
                className="rounded border border-purple-400/40 bg-purple-400/10 px-4 py-2 text-xs uppercase tracking-widest text-purple-400 hover:bg-purple-400/20"
                onClick={onSubmit}
              >
                Submit
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const CAT_COLORS: Record<string, string> = {
  de_escalation: 'text-emerald-400',
  status_quo: 'text-slate-300',
  posturing: 'text-yellow-400',
  non_violent: 'text-orange-400',
  violent: 'text-red-400',
  nuclear: 'text-purple-400',
}

const CAT_LABELS: Record<string, string> = {
  de_escalation: 'De-escalation',
  status_quo: 'Status Quo',
  posturing: 'Posturing',
  non_violent: 'Non-violent',
  violent: 'Violent',
  nuclear: 'Nuclear',
}

export function RoundRecapModal({ recap, onClose }: { recap: RoundRecap; onClose: () => void }) {
  const topMover = [...recap.standings].sort((a, b) => b.delta - a.delta)[0]
  const biggestDrop = [...recap.standings].sort((a, b) => a.delta - b.delta)[0]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-lg border border-warroom-amber/50 bg-slate-900/95 p-6 shadow-2xl shadow-warroom-amber/20">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-700/60 pb-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em] text-warroom-amber/70">Intelligence Debrief</p>
            <h2 className="font-pixel text-xl text-warroom-amber">Round {recap.round_number} Recap</h2>
          </div>
          <button className="rounded border border-slate-700 px-3 py-1.5 text-xs uppercase tracking-widest text-slate-400 hover:border-warroom-amber/50 hover:text-warroom-amber" onClick={onClose}>
            Continue
          </button>
        </div>

        {/* Action summary bar */}
        <div className="mt-4 flex flex-wrap gap-3 text-xs">
          <div className="rounded border border-slate-700/60 bg-warroom-blue/40 px-3 py-1.5">
            <span className="text-slate-500">Actions: </span>
            <span className="text-slate-100 font-semibold">{recap.summary.total_actions}</span>
          </div>
          <div className="rounded border border-emerald-500/30 bg-emerald-900/15 px-3 py-1.5">
            <span className="text-slate-500">Succeeded: </span>
            <span className="text-emerald-400 font-semibold">{recap.summary.successful}</span>
          </div>
          <div className="rounded border border-red-500/30 bg-red-900/15 px-3 py-1.5">
            <span className="text-slate-500">Failed: </span>
            <span className="text-red-400 font-semibold">{recap.summary.failed}</span>
          </div>
          {Object.entries(recap.summary.by_category)
            .filter(([cat]) => cat !== 'status_quo')
            .sort(([, a], [, b]) => b - a)
            .map(([cat, count]) => (
              <div key={cat} className="rounded border border-slate-700/40 bg-warroom-blue/20 px-3 py-1.5">
                <span className={CAT_COLORS[cat] ?? 'text-slate-300'}>{CAT_LABELS[cat] ?? cat}: </span>
                <span className="text-slate-100">{count}</span>
              </div>
            ))
          }
        </div>

        {/* Your team results */}
        {recap.my_stats && (
          <div className="mt-5 rounded border border-warroom-cyan/40 bg-warroom-cyan/5 p-4">
            <p className="text-[10px] uppercase tracking-[0.25em] text-warroom-cyan/70 mb-3">Your Nation Status</p>
            <div className="grid grid-cols-4 gap-3 text-center text-sm">
              <div>
                <p className="text-[10px] uppercase text-slate-500">Prosperity</p>
                <p className="text-lg font-semibold text-emerald-400">{recap.my_stats.prosperity}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase text-slate-500">Security</p>
                <p className="text-lg font-semibold text-blue-400">{recap.my_stats.security}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase text-slate-500">Influence</p>
                <p className="text-lg font-semibold text-purple-400">{recap.my_stats.influence}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase text-slate-500">Escalation</p>
                <p className={`text-lg font-semibold ${recap.my_stats.escalation > 20 ? 'text-red-400' : recap.my_stats.escalation > 10 ? 'text-warroom-amber' : 'text-slate-300'}`}>{recap.my_stats.escalation}</p>
              </div>
            </div>
            {recap.my_actions.length > 0 && (
              <div className="mt-3 border-t border-slate-700/50 pt-3">
                <p className="text-[10px] uppercase tracking-widest text-slate-500 mb-2">Your Actions This Round</p>
                {recap.my_actions.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className={`text-[10px] uppercase font-semibold ${CAT_COLORS[a.category] ?? 'text-slate-400'}`}>Slot {a.slot}</span>
                    <span className="text-slate-200">{a.action_name}</span>
                    {a.target && <span className="text-slate-500">on <span className="text-slate-300">{a.target}</span></span>}
                    <span className={`ml-auto text-xs font-semibold ${a.success ? 'text-emerald-400' : 'text-red-400'}`}>
                      {a.success ? 'SUCCESS' : 'FAILED'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Narrative */}
        {recap.narrative && (
          <div className="mt-5">
            <p className="text-[10px] uppercase tracking-[0.25em] text-warroom-amber/70 mb-2">Situation Report</p>
            <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-4 text-sm text-slate-300 leading-relaxed whitespace-pre-line">
              {recap.narrative}
            </div>
          </div>
        )}

        {/* Events feed */}
        {recap.events.length > 0 && (
          <div className="mt-5">
            <p className="text-[10px] uppercase tracking-[0.25em] text-warroom-amber/70 mb-2">Intelligence Feed</p>
            <div className="max-h-48 overflow-y-auto rounded border border-slate-700/60 bg-warroom-blue/20 divide-y divide-slate-700/40">
              {recap.events.map((ev, i) => (
                <div key={i} className="px-4 py-2 text-sm text-slate-300">
                  <span className="text-warroom-amber mr-2 text-xs font-mono">{String(i + 1).padStart(2, '0')}</span>
                  {ev}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Standings table */}
        <div className="mt-5">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] uppercase tracking-[0.25em] text-warroom-amber/70">Global Standings</p>
            <div className="flex gap-4 text-[10px] text-slate-500">
              {topMover && topMover.delta > 0 && <span>Top mover: <span className="text-emerald-400">{topMover.nation_name} (+{topMover.delta})</span></span>}
              {biggestDrop && biggestDrop.delta < 0 && <span>Biggest drop: <span className="text-red-400">{biggestDrop.nation_name} ({biggestDrop.delta})</span></span>}
            </div>
          </div>
          <div className="overflow-hidden rounded border border-slate-700/60">
            <table className="w-full text-sm">
              <thead className="bg-slate-800/60 text-[10px] uppercase tracking-widest text-slate-500">
                <tr>
                  <th className="px-3 py-2 text-left">#</th>
                  <th className="px-3 py-2 text-left">Nation</th>
                  <th className="px-3 py-2 text-right">Score</th>
                  <th className="px-3 py-2 text-right">Change</th>
                  <th className="px-3 py-2 text-right">Escalation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {recap.standings.map((s, i) => (
                  <tr key={s.team_id}>
                    <td className="px-3 py-1.5 text-warroom-amber font-pixel text-xs">{i + 1}</td>
                    <td className="px-3 py-1.5 text-slate-200">{s.nation_name}</td>
                    <td className="px-3 py-1.5 text-right text-slate-200">{s.score}</td>
                    <td className={`px-3 py-1.5 text-right font-semibold ${s.delta > 0 ? 'text-emerald-400' : s.delta < 0 ? 'text-red-400' : 'text-slate-500'}`}>
                      {s.delta > 0 ? '+' : ''}{s.delta}
                    </td>
                    <td className={`px-3 py-1.5 text-right ${s.escalation > 20 ? 'text-red-400' : s.escalation > 10 ? 'text-warroom-amber' : 'text-slate-400'}`}>
                      {s.escalation}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* World state */}
        <div className="mt-5 flex items-center justify-between rounded border border-slate-700/40 bg-warroom-blue/20 px-4 py-3 text-sm">
          <div className="flex items-center gap-4">
            <span className="text-[10px] uppercase tracking-widest text-slate-500">Global Escalation:</span>
            <span className={`font-semibold ${recap.world.total_escalation >= 60 ? 'text-red-400' : recap.world.total_escalation >= 40 ? 'text-warroom-amber' : 'text-slate-300'}`}>
              {recap.world.total_escalation}
            </span>
          </div>
          {recap.world.nuke_unlocked && (
            <span className="text-[10px] uppercase tracking-widest text-red-400 font-semibold animate-pulse">Nuclear weapons unlocked</span>
          )}
        </div>

        {/* Close button */}
        <div className="mt-6 flex justify-center">
          <button
            className="rounded border border-warroom-amber/50 bg-warroom-amber/10 px-8 py-2.5 text-sm uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/20 font-semibold"
            onClick={onClose}
          >
            Proceed to Round {recap.round_number + 1}
          </button>
        </div>
      </div>
    </div>
  )
}

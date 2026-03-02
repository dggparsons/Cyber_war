import { useMemo, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { LeaderboardResponse, RevealData, HistoryEntry } from '../lib/api'
import type { GameState } from '../lib/gameUtils'
import { NATION_COLORS } from '../lib/gameUtils'
import { ChatComposer } from './ChatComposer'
import { RevealView } from './RevealView'

type ChatMessage = { display_name: string; content: string; role?: string }
type TypingUser = { display_name: string }

type Props = {
  data: GameState
  leaderboard: LeaderboardResponse | null
  messages: ChatMessage[]
  typingUsers: TypingUser[]
  sendMessage: (msg: string) => void
  sendTyping: (typing: boolean) => void
  chatCollapsed: boolean
  onToggleChat: () => void
  historyEntries: HistoryEntry[]
  shouldShowReveal: boolean
  revealData: RevealData | null
}

export function GameSidebar({
  data, leaderboard, messages, typingUsers, sendMessage, sendTyping,
  chatCollapsed, onToggleChat,
  historyEntries, shouldShowReveal, revealData,
}: Props) {
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Build escalation chart data from leaderboard.escalation_series
  const escalationChartData = useMemo(() => {
    if (!leaderboard?.escalation_series) return []
    const nations = Object.keys(leaderboard.escalation_series)
    if (nations.length === 0) return []
    const maxRounds = Math.max(...nations.map((n) => leaderboard.escalation_series[n]?.length ?? 0))
    if (maxRounds === 0) return []
    const rows: Record<string, number | string>[] = []
    for (let i = 0; i < maxRounds; i++) {
      const row: Record<string, number | string> = { round: i + 1 }
      for (const nation of nations) {
        const series = leaderboard.escalation_series[nation]
        row[nation] = series?.[i]?.score ?? 0
      }
      rows.push(row)
    }
    return rows
  }, [leaderboard?.escalation_series])

  const escalationNations = leaderboard?.escalation_series ? Object.keys(leaderboard.escalation_series) : []

  return (
    <aside className="space-y-6">
      {/* Leaderboard */}
      {leaderboard && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow shadow-warroom-cyan/10">
          <h3 className="font-pixel text-xs text-warroom-cyan">Outcome Leaderboard</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {leaderboard.entries.slice(0, 5).map((entry, idx) => (
              <li key={entry.team_id} className="flex items-center justify-between text-slate-300">
                <span><span className="mr-2 text-warroom-amber">#{idx + 1}</span>{entry.nation_name}</span>
                <span className="font-semibold text-warroom-cyan">{entry.score}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Escalation Trends Chart */}
      {escalationChartData.length > 1 && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
          <h3 className="font-pixel text-xs text-warroom-cyan">Outcome Trends</h3>
          <div className="mt-2" style={{ width: '100%', height: 180 }}>
            <ResponsiveContainer>
              <LineChart data={escalationChartData}>
                <XAxis dataKey="round" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} width={35} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: 11 }} />
                {escalationNations.map((nation, idx) => (
                  <Line key={nation} type="monotone" dataKey={nation} stroke={NATION_COLORS[idx % NATION_COLORS.length]} strokeWidth={1.5} dot={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Roster */}
      <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
        <h3 className="font-pixel text-xs text-warroom-cyan">Team Roster</h3>
        <ul className="mt-2 space-y-1 text-xs text-slate-300">
          {data.roster?.map((member) => (
            <li key={member.id} className="flex items-center gap-2">
              <span className={member.role === 'gm' || member.role === 'admin' ? 'text-red-400' : member.is_captain ? 'text-warroom-amber' : 'text-slate-100'}>
                {member.display_name}
              </span>
              {member.is_captain && <span className="text-[9px] uppercase text-warroom-amber">(Captain)</span>}
              {(member.role === 'gm' || member.role === 'admin') && <span className="text-[9px] uppercase text-red-400">(GM)</span>}
            </li>
          ))}
        </ul>
      </div>

      {/* Team Chat */}
      <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 flex flex-col gap-3 min-h-[300px]">
        <div className="flex items-center justify-between">
          <h3 className="font-pixel text-xs text-warroom-cyan">Team Comms</h3>
          <button className="text-[10px] text-slate-400 hover:text-slate-200" onClick={onToggleChat}>
            {chatCollapsed ? 'Expand' : 'Collapse'}
          </button>
        </div>
        {!chatCollapsed && (
          <>
            <div className="flex-1 overflow-y-auto rounded border border-slate-700/60 bg-warroom-blue/40 p-3 text-sm text-slate-300 min-h-[200px]">
              {messages.map((line, idx) => (
                <p key={idx}>
                  <span className={
                    line.role === 'gm' || line.role === 'admin' ? 'text-red-400 font-semibold' :
                    line.role === 'advisor' ? 'text-warroom-amber' :
                    'text-warroom-cyan'
                  }>{line.display_name}:</span> {line.content}
                </p>
              ))}
              <div ref={chatEndRef} />
            </div>
            {typingUsers.length > 0 && (
              <p className="text-[10px] text-slate-400 italic">
                {typingUsers.map((u) => u.display_name).join(', ')} typing...
              </p>
            )}
            <ChatComposer onSend={sendMessage} onTyping={sendTyping} />
          </>
        )}
      </div>

      {/* World News */}
      <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
        <h3 className="font-pixel text-xs text-warroom-cyan">World News</h3>
        <p className="mt-2 text-slate-300">{data.narrative}</p>
      </div>

      {/* Reveal */}
      {shouldShowReveal && revealData && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
          <RevealView data={revealData} />
        </div>
      )}

      {/* History */}
      <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
        <h3 className="font-pixel text-xs text-warroom-cyan">Round History</h3>
        <div className="mt-2 max-h-48 overflow-y-auto space-y-1 text-xs text-slate-400">
          {historyEntries.length === 0 && <p>No actions resolved yet.</p>}
          {historyEntries.map((entry) => (
            <div key={entry.id} className="rounded border border-slate-700/50 bg-slate-800/40 p-2">
              <p className="text-slate-200">
                Round {entry.round} — {entry.actor ?? 'Unknown'} used {entry.action_code}
                {entry.target ? ` on ${entry.target}` : ''} ({entry.success ? 'SUCCESS' : 'FAILED'})
              </p>
              <p className="text-[10px] uppercase tracking-widest text-slate-500">Slot {entry.slot}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}

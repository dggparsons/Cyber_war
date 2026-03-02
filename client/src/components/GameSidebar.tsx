import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import type { LeaderboardResponse, RevealData, HistoryEntry } from '../lib/api'
import type { GameState } from '../lib/gameUtils'
import { NATION_COLORS } from '../lib/gameUtils'
import { RevealView } from './RevealView'
import { DiplomacyPanel } from './DiplomacyPanel'
import { IntelPanel } from './IntelPanel'
import type { MegaChallengeData } from '../lib/api'
import type { IntelDropItem } from './modals'

type DiplomacyProps = {
  teamId: number
  channels: any[]
  drafts: Record<number, string>
  target: number | ''
  unread: number
  teamOptions: Array<{ team_id: number; nation_name: string }>
  alliances: any[]
  leaderboard: LeaderboardResponse | null
  onTargetChange: (val: number | '') => void
  onStart: () => void
  onSend: (channelId: number) => void
  onDraftChange: (channelId: number, val: string) => void
  onRespond: (channelId: number, action: 'accept' | 'decline') => void
  onClick: () => void
}

type IntelProps = {
  drops: Array<{ id: number; title: string; description: string; reward: string; status: string }>
  megaChallenge: MegaChallengeData | null
  onSelectIntel: (intel: IntelDropItem) => void
  onOpenMega: () => void
}

type Props = {
  data: GameState
  leaderboard: LeaderboardResponse | null
  historyEntries: HistoryEntry[]
  shouldShowReveal: boolean
  revealData: RevealData | null
  diplomacy: DiplomacyProps
  intel: IntelProps
}

export function GameSidebar({
  data, leaderboard,
  historyEntries, shouldShowReveal, revealData, diplomacy, intel,
}: Props) {

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

      {/* Diplomacy */}
      <DiplomacyPanel
        teamId={diplomacy.teamId}
        diplomacyChannels={diplomacy.channels}
        diplomacyDrafts={diplomacy.drafts}
        diplomacyTarget={diplomacy.target}
        diplomacyUnread={diplomacy.unread}
        teamOptions={diplomacy.teamOptions}
        alliances={diplomacy.alliances}
        leaderboard={diplomacy.leaderboard}
        onDiplomacyTargetChange={diplomacy.onTargetChange}
        onStartDiplomacy={diplomacy.onStart}
        onSendDiplomacy={diplomacy.onSend}
        onDiplomacyDraftChange={diplomacy.onDraftChange}
        onRespondDiplomacy={diplomacy.onRespond}
        onDiplomacyClick={diplomacy.onClick}
      />

      {/* Intel Drops */}
      <IntelPanel
        intelDrops={intel.drops}
        megaChallenge={intel.megaChallenge}
        onSelectIntel={intel.onSelectIntel}
        onOpenMega={intel.onOpenMega}
      />

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

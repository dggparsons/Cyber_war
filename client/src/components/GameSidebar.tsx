import { useState } from 'react'
import type { LeaderboardResponse, RevealData, HistoryEntry } from '../lib/api'
import type { GameState } from '../lib/gameUtils'
import { RevealView } from './RevealView'
import { RelationshipsPanel } from './RelationshipsPanel'

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

type Props = {
  data: GameState
  leaderboard: LeaderboardResponse | null
  historyEntries: HistoryEntry[]
  shouldShowReveal: boolean
  revealData: RevealData | null
  diplomacy: DiplomacyProps
  briefingAllies: string[]
  briefingThreats: string[]
}

export function GameSidebar({
  data, leaderboard,
  historyEntries, shouldShowReveal, revealData, diplomacy,
  briefingAllies, briefingThreats,
}: Props) {

  const [leaderboardExpanded, setLeaderboardExpanded] = useState(false)
  const visibleEntries = leaderboard?.entries
    ? leaderboardExpanded ? leaderboard.entries : leaderboard.entries.slice(0, 5)
    : []
  const canExpand = (leaderboard?.entries.length ?? 0) > 5

  return (
    <aside className="space-y-6">
      {/* Leaderboard */}
      {leaderboard && (
        <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow shadow-warroom-cyan/10">
          <div className="flex items-center justify-between">
            <h3 className="font-pixel text-xs text-warroom-cyan">Leaderboard</h3>
            {canExpand && (
              <button
                onClick={() => setLeaderboardExpanded((v) => !v)}
                className="text-[10px] text-warroom-cyan/70 hover:text-warroom-cyan transition-colors"
              >
                {leaderboardExpanded ? 'Show less' : `Show all (${leaderboard.entries.length})`}
              </button>
            )}
          </div>
          <ul className="mt-3 space-y-2 text-sm">
            {visibleEntries.map((entry, idx) => (
              <li key={entry.team_id} className="flex items-center justify-between text-slate-300">
                <span><span className="mr-2 text-warroom-amber">#{idx + 1}</span>{entry.nation_name}</span>
                <span className="font-semibold text-warroom-cyan">{entry.score}</span>
              </li>
            ))}
          </ul>
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

      {/* Relationships */}
      <RelationshipsPanel
        briefingAllies={briefingAllies}
        briefingThreats={briefingThreats}
        alliances={diplomacy.alliances}
        teamId={diplomacy.teamId}
        leaderboard={leaderboard}
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

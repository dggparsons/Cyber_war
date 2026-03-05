import { useEffect, useRef } from 'react'
import type { LeaderboardResponse } from '../lib/api'

type DiplomacyChannel = any
type TeamOption = { team_id: number; nation_name: string }

type Props = {
  teamId: number
  diplomacyChannels: DiplomacyChannel[]
  diplomacyDrafts: Record<number, string>
  diplomacyTarget: number | ''
  diplomacyUnread: number
  teamOptions: TeamOption[]
  alliances: Array<{ team_a_id: number; team_b_id: number; status: string; formed_at: string | null }>
  leaderboard: LeaderboardResponse | null
  onDiplomacyTargetChange: (value: number | '') => void
  onStartDiplomacy: () => void
  onSendDiplomacy: (channelId: number) => void
  onDiplomacyDraftChange: (channelId: number, value: string) => void
  onRespondDiplomacy: (channelId: number, action: 'accept' | 'decline') => void
  onDiplomacyClick: () => void
}

function ChatMessages({ messages, teamId, otherName }: { messages: any[]; teamId: number; otherName: string }) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages.length])

  return (
    <div ref={scrollRef} className="mt-2 max-h-48 overflow-y-auto space-y-1.5 px-1 scrollbar-thin">
      {messages.length === 0 && <p className="text-[10px] italic text-slate-500 text-center py-2">No messages yet. Say hello!</p>}
      {messages.map((msg: any) => {
        const isOurs = msg.team_id === teamId
        return (
          <div key={msg.id} className={`flex ${isOurs ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg px-2.5 py-1.5 text-xs ${
              isOurs
                ? 'bg-warroom-cyan/20 border border-warroom-cyan/30 text-slate-200'
                : 'bg-slate-700/60 border border-slate-600/40 text-slate-300'
            }`}>
              <p className={`text-[9px] font-semibold mb-0.5 ${isOurs ? 'text-warroom-cyan' : 'text-warroom-amber'}`}>
                {isOurs ? (msg.display_name ?? 'You') : `${otherName} · ${msg.display_name ?? 'Unknown'}`}
              </p>
              <p className="break-words leading-relaxed">{msg.content}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function DiplomacyPanel({
  teamId, diplomacyChannels, diplomacyDrafts, diplomacyTarget, diplomacyUnread,
  teamOptions, alliances, leaderboard,
  onDiplomacyTargetChange, onStartDiplomacy, onSendDiplomacy,
  onDiplomacyDraftChange, onRespondDiplomacy, onDiplomacyClick,
}: Props) {
  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10 text-sm text-slate-200" onClick={onDiplomacyClick}>
      <h2 className="font-pixel text-sm text-warroom-cyan flex items-center gap-2">
        Diplomacy
        {diplomacyUnread > 0 && (
          <span className="inline-flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-warroom-amber px-1 text-[10px] font-bold text-slate-900 animate-pulse">
            {diplomacyUnread}
          </span>
        )}
      </h2>

      <div className="mt-3 flex items-center gap-2">
        <select className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-xs" value={diplomacyTarget} onChange={(e) => onDiplomacyTargetChange(Number(e.target.value))}>
          <option value="">Select nation</option>
          {teamOptions.map((entry) => (
            <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
          ))}
        </select>
        <button className="rounded border border-slate-600 bg-warroom-cyan/30 px-3 py-1 text-xs hover:bg-warroom-cyan/50 transition-colors" onClick={onStartDiplomacy}>Open Channel</button>
      </div>

      <div className="mt-3 space-y-3 max-h-[500px] overflow-y-auto">
        {diplomacyChannels.length === 0 && <p className="text-xs text-slate-500">No diplomacy channels yet.</p>}
        {diplomacyChannels.map((channel: any) => {
          const otherName = channel.with_team?.nation_name ?? 'Unknown'
          return (
            <div key={channel.channel_id} className="rounded border border-slate-700/70 bg-warroom-blue/40 p-2">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase text-slate-400">
                  <span className="text-warroom-amber font-semibold">{otherName}</span>
                </p>
                <span className={`text-[9px] uppercase font-bold tracking-wider ${channel.status === 'accepted' ? 'text-green-400' : 'text-warroom-amber'}`}>
                  {channel.status === 'accepted' ? 'Active' : 'Pending'}
                </span>
              </div>
              {channel.status === 'pending' && !channel.is_initiator && (
                <div className="mt-2 flex gap-2">
                  <button className="flex-1 rounded border border-green-600 bg-green-700/30 py-1 text-xs text-green-300 hover:bg-green-700/50" onClick={() => onRespondDiplomacy(channel.channel_id, 'accept')}>Accept</button>
                  <button className="flex-1 rounded border border-red-600 bg-red-700/30 py-1 text-xs text-red-300 hover:bg-red-700/50" onClick={() => onRespondDiplomacy(channel.channel_id, 'decline')}>Decline</button>
                </div>
              )}
              {channel.status === 'pending' && channel.is_initiator && (
                <p className="mt-2 text-[10px] italic text-slate-500">Waiting for response...</p>
              )}
              {channel.status === 'accepted' && (
                <>
                  <ChatMessages messages={channel.messages} teamId={teamId} otherName={otherName} />
                  <div className="mt-2 flex gap-1.5">
                    <input
                      className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1.5 text-xs focus:border-warroom-cyan/50 focus:outline-none"
                      placeholder={`Message ${otherName}...`}
                      value={diplomacyDrafts[channel.channel_id] ?? ''}
                      onChange={(e) => onDiplomacyDraftChange(channel.channel_id, e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') onSendDiplomacy(channel.channel_id) }}
                    />
                    <button className="rounded border border-slate-600 bg-warroom-amber/30 px-3 py-1.5 text-xs hover:bg-warroom-amber/50 transition-colors" onClick={() => onSendDiplomacy(channel.channel_id)}>Send</button>
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>

      {alliances.length > 0 && (
        <div className="mt-3 rounded border border-slate-700/70 bg-warroom-blue/30 p-2">
          <p className="text-xs uppercase text-slate-400">Active Alliances</p>
          <ul className="mt-1 space-y-1 text-xs text-slate-300">
            {alliances.map((alliance) => {
              const partner =
                alliance.team_a_id === teamId
                  ? leaderboard?.entries.find((entry) => entry.team_id === alliance.team_b_id)?.nation_name
                  : leaderboard?.entries.find((entry) => entry.team_id === alliance.team_a_id)?.nation_name
              return <li key={`${alliance.team_a_id}-${alliance.team_b_id}`}>{partner ?? 'Unknown partner'}</li>
            })}
          </ul>
        </div>
      )}
    </section>
  )
}

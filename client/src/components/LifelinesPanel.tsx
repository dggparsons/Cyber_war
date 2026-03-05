import { useState } from 'react'

type Lifeline = { id: number; lifeline_type: string; remaining_uses: number; awarded_for?: string | null }
type PhoneHint = { team_name: string; action_name: string; slot: number }

type Props = {
  lifelines: Lifeline[]
  phoneHint: PhoneHint | null
  teamOptions: Array<{ team_id: number; nation_name: string }>
  onUsePhoneAFriend: (targetTeamId: number) => void
  onDismissHint: () => void
}

export function LifelinesPanel({ lifelines, phoneHint, teamOptions, onUsePhoneAFriend, onDismissHint }: Props) {
  const [phoneTarget, setPhoneTarget] = useState<number | ''>('')
  return (
    <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4">
      <h3 className="font-pixel text-xs text-warroom-cyan">Lifelines</h3>
      {lifelines.length === 0 && <p className="mt-2 text-xs text-slate-400">No lifelines available. Solve intel drops to earn them.</p>}
      {lifelines.length > 0 && (
        <ul className="mt-2 space-y-2 text-xs text-slate-300">
          {lifelines.map((lifeline) => (
            <li key={lifeline.id} className="rounded border border-slate-700/50 bg-warroom-blue/30 px-2 py-1.5">
              <span className="font-semibold text-slate-100">{lifeline.lifeline_type.replace(/_/g, ' ')}</span>: {lifeline.remaining_uses} remaining
              {lifeline.lifeline_type === 'false_flag' && (
                <p className="mt-1 text-[10px] text-slate-400">Submit a covert action, then use the "Blame" dropdown to frame another nation. The escalation and attribution shifts to them.</p>
              )}
              {lifeline.lifeline_type === 'phone_a_friend' && (
                <p className="mt-1 text-[10px] text-slate-400">Spy on a random enemy team to see what action they're planning this round.</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {lifelines.some((l) => l.lifeline_type === 'phone_a_friend' && l.remaining_uses > 0) && (
        <div className="mt-2 flex gap-2">
          <select
            value={phoneTarget}
            onChange={(e) => setPhoneTarget(e.target.value ? Number(e.target.value) : '')}
            className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1.5 text-xs text-slate-200"
          >
            <option value="">Select target...</option>
            {teamOptions.map((t) => (
              <option key={t.team_id} value={t.team_id}>{t.nation_name}</option>
            ))}
          </select>
          <button
            className="rounded border border-warroom-amber/40 bg-warroom-amber/10 px-3 py-1.5 text-xs uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/20 disabled:opacity-40 disabled:cursor-not-allowed"
            onClick={() => { if (phoneTarget) { onUsePhoneAFriend(phoneTarget); setPhoneTarget('') } }}
            disabled={!phoneTarget}
          >
            Spy
          </button>
        </div>
      )}
      {phoneHint && (
        <div className="mt-2 rounded border border-warroom-amber/40 bg-warroom-amber/10 p-2 text-xs text-warroom-amber">
          <p className="font-semibold">Intel Received:</p>
          <p><span className="font-bold">{phoneHint.team_name}</span> is planning <span className="font-bold text-warroom-cyan">{phoneHint.action_name}</span></p>
          <button className="mt-1 text-[10px] text-slate-400 underline" onClick={onDismissHint}>Dismiss</button>
        </div>
      )}
    </div>
  )
}

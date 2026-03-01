type Lifeline = { id: number; lifeline_type: string; remaining_uses: number; awarded_for?: string | null }
type PhoneHint = { team_name: string; action_name: string; slot: number }

type Props = {
  lifelines: Lifeline[]
  phoneHint: PhoneHint | null
  onUsePhoneAFriend: () => void
  onDismissHint: () => void
}

export function LifelinesPanel({ lifelines, phoneHint, onUsePhoneAFriend, onDismissHint }: Props) {
  return (
    <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4">
      <h3 className="font-pixel text-xs text-warroom-cyan">Lifelines</h3>
      {lifelines.length === 0 && <p className="mt-2 text-xs text-slate-400">No lifelines available.</p>}
      {lifelines.length > 0 && (
        <ul className="mt-2 space-y-1 text-xs text-slate-300">
          {lifelines.map((lifeline) => (
            <li key={lifeline.id} className="rounded border border-slate-700/50 bg-warroom-blue/30 px-2 py-1">
              <span className="font-semibold text-slate-100">{lifeline.lifeline_type.replace(/_/g, ' ')}</span>: {lifeline.remaining_uses} remaining
            </li>
          ))}
        </ul>
      )}
      {lifelines.some((l) => l.lifeline_type === 'phone_a_friend' && l.remaining_uses > 0) && (
        <button
          className="mt-2 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1.5 text-xs uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/20"
          onClick={onUsePhoneAFriend}
        >
          Phone-a-Friend
        </button>
      )}
      {phoneHint && (
        <div className="mt-2 rounded border border-warroom-amber/40 bg-warroom-amber/10 p-2 text-xs text-warroom-amber">
          <p className="font-semibold">Intel Received:</p>
          <p>{phoneHint.team_name} is planning <span className="font-bold">{phoneHint.action_name}</span> in slot {phoneHint.slot}</p>
          <button className="mt-1 text-[10px] text-slate-400 underline" onClick={onDismissHint}>Dismiss</button>
        </div>
      )}
    </div>
  )
}

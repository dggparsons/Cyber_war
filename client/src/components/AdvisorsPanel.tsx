type Advisor = { name: string; mood: string; hint: string; avatar?: string }

type Props = {
  advisors: Advisor[]
}

const MOOD_COLORS: Record<string, string> = {
  hawkish: 'text-red-400',
  aggressive: 'text-red-400',
  chaotic: 'text-red-400',
  paranoid: 'text-orange-400',
  propaganda: 'text-orange-400',
  deceptive: 'text-purple-400',
  calculated: 'text-purple-400',
  analytical: 'text-blue-400',
  precise: 'text-blue-400',
  innovative: 'text-emerald-400',
  diplomatic: 'text-green-400',
  calm: 'text-green-400',
  peaceful: 'text-green-400',
  humanitarian: 'text-pink-400',
  protective: 'text-yellow-400',
  defensive: 'text-cyan-400',
  stoic: 'text-slate-300',
  neutral: 'text-slate-300',
  firm: 'text-amber-400',
  watchful: 'text-sky-400',
}

export function AdvisorsPanel({ advisors }: Props) {
  if (advisors.length === 0) return null

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10">
      <h2 className="font-pixel text-sm text-warroom-cyan">Advisors</h2>
      <div className="mt-3 space-y-3">
        {advisors.map((advisor) => (
          <div key={advisor.name} className="flex gap-3 rounded border border-slate-700/60 p-3">
            {advisor.avatar && (
              <img
                src={advisor.avatar}
                alt={advisor.name}
                className="h-10 w-10 flex-shrink-0 rounded-md border border-slate-600/50"
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-slate-300 truncate">{advisor.name}</p>
                <span className={`flex-shrink-0 text-[9px] uppercase tracking-wider ${MOOD_COLORS[advisor.mood] ?? 'text-warroom-amber'}`}>
                  {advisor.mood}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-100">{advisor.hint}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

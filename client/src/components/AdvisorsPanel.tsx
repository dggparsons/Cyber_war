type Advisor = { name: string; mood: string; hint: string }

type Props = {
  advisors: Advisor[]
}

export function AdvisorsPanel({ advisors }: Props) {
  if (advisors.length === 0) return null

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10">
      <h2 className="font-pixel text-sm text-warroom-cyan">Advisors</h2>
      <div className="mt-3 space-y-3">
        {advisors.map((advisor) => (
          <div key={advisor.name} className="rounded border border-slate-700/60 p-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-slate-300">{advisor.name}</p>
              <span className="text-[9px] uppercase tracking-wider text-warroom-amber">{advisor.mood}</span>
            </div>
            <p className="mt-1 text-sm text-slate-100">{advisor.hint}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

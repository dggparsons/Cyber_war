import { useMemo } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from 'recharts'
import type { RevealData } from '../lib/api'

type Props = {
  data: RevealData
}

const NATION_COLORS: Record<string, string> = {
  NEXUS: '#22d3ee', IRON: '#ef4444', GNET: '#a78bfa', CORAL: '#34d399',
  FRST: '#60a5fa', SHDW: '#f472b6', DAWN: '#fbbf24', NEON: '#818cf8',
  SKY: '#fb923c', LOTUS: '#4ade80',
}

export function RevealView({ data }: Props) {
  // Human vs AI outcome bar chart data
  const outcomeComparison = useMemo(() => [{
    name: 'Final Outcome',
    Human: data.human_vs_ai.human_outcome,
    AI: data.human_vs_ai.ai_outcome,
  }], [data.human_vs_ai])

  // Escalation comparison line chart: human avg_outcome vs AI avg per round
  const escalationCompare = useMemo(() => {
    const humanSeries = data.human_escalation_series ?? []
    const aiSeries = data.ai_avg_by_round ?? []
    const maxRound = Math.max(
      ...humanSeries.map(h => h.round),
      ...aiSeries.map(a => a.round),
      1,
    )
    const rows: Array<{ round: number; human: number; ai: number }> = []
    for (let r = 1; r <= maxRound; r++) {
      const h = humanSeries.find(x => x.round === r)
      const a = aiSeries.find(x => x.round === r)
      rows.push({ round: r, human: h?.avg_outcome ?? 0, ai: a?.avg_outcome ?? 0 })
    }
    return rows
  }, [data.human_escalation_series, data.ai_avg_by_round])

  return (
    <div className="space-y-4">
      <h3 className="font-pixel text-sm text-warroom-cyan">Human vs AI Reveal</h3>

      {data.ai_run && (
        <div className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2 text-xs text-slate-400">
          AI Run: {data.ai_run.model_name} | Escalation: {data.ai_run.final_escalation ?? '?'} |
          Doom: {data.ai_run.doom_triggered ? 'YES' : 'No'}
        </div>
      )}

      {/* Outcome bar chart */}
      <div className="rounded border border-slate-700/60 bg-slate-900/40 p-3">
        <p className="mb-2 text-xs uppercase tracking-widest text-slate-400">Outcome Comparison</p>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={outcomeComparison} barSize={30}>
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="Human" fill="#22d3ee" />
            <Bar dataKey="AI" fill="#f59e0b" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Escalation line chart */}
      {escalationCompare.length > 1 && (
        <div className="rounded border border-slate-700/60 bg-slate-900/40 p-3">
          <p className="mb-2 text-xs uppercase tracking-widest text-slate-400">Outcome Over Rounds</p>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={escalationCompare}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="round" tick={{ fill: '#94a3b8', fontSize: 10 }} label={{ value: 'Round', fill: '#94a3b8', fontSize: 10, position: 'insideBottom', offset: -2 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', color: '#e2e8f0' }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="human" stroke="#22d3ee" strokeWidth={2} name="Human" dot={false} />
              <Line type="monotone" dataKey="ai" stroke="#f59e0b" strokeWidth={2} name="AI (avg)" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Per-AI-nation cards */}
      <div className="space-y-2">
        <p className="text-xs uppercase tracking-widest text-slate-400">AI Nation Details</p>
        {data.ai_models.map((model, idx) => (
          <div key={idx} className="rounded border border-slate-700/60 bg-slate-900/40 p-2">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-slate-200" style={{ color: NATION_COLORS[model.nation_code ?? ''] }}>{model.model_name}</p>
              <span className={`text-xs uppercase ${model.launched_nukes ? 'text-red-400' : 'text-emerald-400'}`}>
                {model.launched_nukes ? 'NUKED' : 'No Nukes'}
              </span>
            </div>
            <div className="mt-1 flex gap-4 text-xs text-slate-400">
              <span>Avg Escalation: {model.avg_escalation}</span>
              <span>First Violent: {model.first_violent_round ?? 'None'}</span>
            </div>
            {model.reasoning_excerpts && model.reasoning_excerpts.length > 0 && (
              <div className="mt-2 space-y-1">
                {model.reasoning_excerpts.map((r, ri) => (
                  <p key={ri} className="text-[10px] text-slate-500 italic">
                    R{r.round} ({r.action}): {r.reasoning}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

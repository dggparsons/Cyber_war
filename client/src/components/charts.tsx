import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'
import { NATION_COLORS } from '../lib/gameUtils'

export function EscalationChart({ series }: { series: Record<string, Array<{ round: number; score: number }>> | Array<{ round: number; score: number }> }) {
  if (Array.isArray(series)) {
    if (series.length === 0) return <p className="text-xs text-slate-500">Waiting for data...</p>
    const chartData = series.map((point) => ({ round: `R${point.round}`, escalation: point.score }))
    return (
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="round" stroke="#94a3b8" fontSize={10} />
          <YAxis stroke="#94a3b8" fontSize={10} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
          <Line type="monotone" dataKey="escalation" stroke="#ef4444" strokeWidth={2} dot={{ fill: '#ef4444' }} />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  const nations = Object.keys(series)
  if (nations.length === 0) return <p className="text-xs text-slate-500">Waiting for data...</p>
  const maxRounds = Math.max(...nations.map((n) => series[n].length))
  if (maxRounds === 0) return <p className="text-xs text-slate-500">No rounds resolved yet.</p>

  const chartData = Array.from({ length: maxRounds }, (_, i) => {
    const point: Record<string, any> = { round: `R${i + 1}` }
    for (const nation of nations) {
      point[nation] = series[nation]?.[i]?.score ?? 0
    }
    return point
  })

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="round" stroke="#94a3b8" fontSize={10} />
        <YAxis stroke="#94a3b8" fontSize={10} />
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc', fontSize: 11 }} />
        {nations.map((nation, idx) => (
          <Line key={nation} type="monotone" dataKey={nation} stroke={NATION_COLORS[idx % NATION_COLORS.length]} strokeWidth={1.5} dot={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export function LeaderboardBarChart({ entries }: { entries: Array<{ nation_name: string; score: number; baseline: number }> }) {
  const data = entries.map((e) => ({
    name: e.nation_name.length > 8 ? e.nation_name.slice(0, 8) + '\u2026' : e.nation_name,
    score: e.score,
    delta: e.score - e.baseline,
  }))
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} angle={-30} textAnchor="end" height={60} />
        <YAxis stroke="#94a3b8" fontSize={10} />
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
        <Bar dataKey="score" fill="#38bdf8" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.delta >= 0 ? '#22c55e' : '#ef4444'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

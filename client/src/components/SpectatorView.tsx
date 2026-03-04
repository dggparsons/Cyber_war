import type { LeaderboardResponse, RevealData, GlobalStatePayload } from '../lib/api'
import type { RoundTimer } from '../hooks/useRoundTimer'
import { formatTimerDisplay } from '../lib/gameUtils'
import { NewsTicker } from './NewsTicker'
import { DoomsdayClock } from './DoomsdayClock'
import { EscalationChart, LeaderboardBarChart } from './charts'

export function SpectatorView({ leaderboard, timer, reveal, news, global }: {
  leaderboard: LeaderboardResponse | null
  timer: RoundTimer
  reveal: RevealData | null
  news: Array<{ id: number; message: string }>
  global?: GlobalStatePayload | null
}) {
  if (!leaderboard) {
    return <div className="flex min-h-screen items-center justify-center bg-warroom-blue text-slate-100">Waiting for game state…</div>
  }
  const timerText = formatTimerDisplay(timer)
  const progress = timer.duration ? Math.max(0, Math.min(1, timer.remaining / timer.duration)) : 0
  const crisis = global?.active_crisis ?? null
  const doomActive = global?.doom_triggered ?? false
  const totalEscalation = global?.total_escalation ?? 0
  return (
    <div className="min-h-screen bg-warroom-blue text-slate-100">
      <NewsTicker news={news} />
      <div className="mx-auto max-w-5xl px-6 py-8">
        <h1 className="font-pixel text-2xl text-warroom-cyan">Cyber War Room — Live Leaderboard</h1>
        <div className="space-y-2">
          <p className="text-sm text-slate-400">
            {timer.state === 'intermission' ? `Next: Round ${timer.round}` : `Round ${timer.round}`} • {timerText}
          </p>
          <div className="h-2 w-48 overflow-hidden rounded-full bg-slate-800/60">
            <div
              className={`h-2 rounded-full ${timer.state === 'paused' ? 'bg-warroom-amber/70 animate-pulse' : timer.state === 'intermission' ? 'bg-purple-500/70 animate-pulse' : 'bg-warroom-cyan/70'}`}
              style={{ width: `${(progress * 100).toFixed(1)}%` }}
            />
          </div>
          {timer.state === 'paused' && <p className="text-xs text-warroom-amber">GM has paused submissions</p>}
          {timer.state === 'intermission' && <p className="text-xs text-purple-400">Intermission — next round starting soon</p>}
          {timer.state === 'complete' && <p className="text-xs text-slate-400">Timer elapsed — awaiting resolution</p>}
          {doomActive && <p className="text-xs text-warroom-amber">Catastrophic strike detected — game over.</p>}
          <div className="flex items-center gap-3">
            <p className="text-xs text-slate-400">Global Escalation: {totalEscalation}</p>
            <DoomsdayClock escalation={totalEscalation} />
          </div>
        </div>
        {crisis && (
          <div className="mt-4 rounded border border-warroom-amber/60 bg-warroom-amber/10 p-4 text-sm text-warroom-amber">
            <p className="font-pixel text-xs uppercase tracking-widest">Active Crisis</p>
            <p className="text-base">{crisis.title}</p>
            <p className="text-warroom-amber/80">{crisis.summary}</p>
            <p className="text-xs text-warroom-amber/70">{crisis.effect}</p>
          </div>
        )}
        <div className="mt-4 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h3 className="font-pixel text-xs text-warroom-cyan">Escalation Trend</h3>
          <EscalationChart series={leaderboard.escalation_series} />
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {leaderboard.entries.map((entry) => (
            <div key={entry.team_id} className="rounded border border-slate-700 bg-slate-900/60 p-4">
              <p className="text-lg font-semibold text-warroom-amber">{entry.nation_name}</p>
              <p className="text-sm text-slate-400">Outcome Score: {entry.score} (Δ {entry.delta_from_baseline})</p>
              <p className="text-xs text-slate-500">Escalation: {entry.escalation}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h3 className="font-pixel text-xs text-warroom-cyan">Score Overview</h3>
          <LeaderboardBarChart entries={leaderboard.entries.map(e => ({ nation_name: e.nation_name, score: e.score, baseline: e.score - (e.delta_from_baseline ?? 0) }))} />
        </div>
        {leaderboard.cyber_impact && leaderboard.cyber_impact.length > 0 && (
          <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h3 className="font-pixel text-xs text-warroom-cyan">Cyber Impact Board</h3>
            <div className="mt-3 max-h-60 overflow-y-auto">
              <table className="w-full text-xs text-slate-300">
                <thead>
                  <tr className="border-b border-slate-700 text-left text-slate-400">
                    <th className="py-1 pr-2">Rd</th>
                    <th className="py-1 pr-2">Attacker</th>
                    <th className="py-1 pr-2">Target</th>
                    <th className="py-1 pr-2">Action</th>
                    <th className="py-1">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.cyber_impact.map((hit, idx) => (
                    <tr key={idx} className="border-b border-slate-800/50">
                      <td className="py-1 pr-2 text-slate-400">{hit.round}</td>
                      <td className="py-1 pr-2 text-warroom-amber">{hit.actor}</td>
                      <td className="py-1 pr-2">{hit.target}</td>
                      <td className="py-1 pr-2">{hit.action.replace(/_/g, ' ')}</td>
                      <td className={`py-1 font-semibold ${hit.success ? 'text-red-400' : 'text-green-400'}`}>
                        {hit.success ? 'HIT' : 'BLOCKED'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
        {reveal && doomActive && (
          <div className="mt-8 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">AI Shadow Comparison</h2>
            <div className="mt-2 grid gap-3 md:grid-cols-3">
              {reveal.ai_models.map((model, index) => (
                <div key={index} className="rounded border border-slate-700/60 bg-slate-900/40 p-3 text-xs text-slate-300">
                  <p className="text-slate-100 font-semibold">{model.model_name}</p>
                  <p>Avg escalation: {Math.round(model.avg_escalation)}</p>
                  <p>First violent round: {model.first_violent_round}</p>
                  <p>{model.launched_nukes ? 'Launched nuclear strike' : 'No nukes'}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-slate-300">Human outcome: {reveal.human_vs_ai.human_outcome} vs AI outcome: {reveal.human_vs_ai.ai_outcome}</p>
          </div>
        )}
      </div>
    </div>
  )
}

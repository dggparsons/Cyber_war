import type { CrisisInfo } from '../lib/api'

export function DoomOverlay({ message }: { message?: string | null }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/80 px-6 text-center">
      <div className="max-w-2xl space-y-4">
        <p className="font-pixel text-3xl text-warroom-amber">☢ GAME OVER — ESCALATION CASCADE</p>
        <p className="text-lg text-slate-100">{message ?? 'A catastrophic strike succeeded. Scenario terminated. Everyone loses.'}</p>
      </div>
    </div>
  )
}

export function CrisisAlert({ crisis }: { crisis: CrisisInfo }) {
  return (
    <div className="pointer-events-none fixed inset-0 z-30 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded border border-warroom-amber/70 bg-warroom-amber/90 p-6 text-center text-slate-900 shadow-2xl shadow-warroom-amber/50">
        <p className="font-pixel text-xs uppercase tracking-[0.4em] text-slate-900">Crisis Alert</p>
        <p className="mt-3 text-2xl font-bold">{crisis.title}</p>
        <p className="mt-2 text-base">{crisis.summary}</p>
        <p className="mt-4 text-sm uppercase tracking-widest text-slate-800">{crisis.effect}</p>
      </div>
    </div>
  )
}

export function EscalationAlert({ flash }: { flash: { threshold: number; severity: string; total: number } }) {
  const color =
    flash.severity === 'doom'
      ? 'bg-red-900/80 border-red-400 text-red-100'
      : flash.severity === 'critical'
        ? 'bg-orange-900/80 border-orange-400 text-orange-100'
        : flash.severity === 'warning'
          ? 'bg-warroom-amber/80 border-warroom-amber text-slate-900'
          : 'bg-warroom-cyan/80 border-warroom-cyan text-slate-900'
  return (
    <div className={`fixed top-2 left-1/2 z-40 w-80 -translate-x-1/2 rounded border px-3 py-2 text-center text-xs font-semibold uppercase tracking-widest screen-shake ${color}`}>
      Global escalation {flash.total} crossed {flash.threshold}
    </div>
  )
}

export function ActiveCrisisBanner({ crisis }: { crisis: CrisisInfo }) {
  return (
    <div className="rounded border border-warroom-amber/60 bg-warroom-amber/10 p-4 text-sm text-warroom-amber">
      <p className="font-pixel text-xs uppercase tracking-widest">Active Crisis</p>
      <p className="text-base">{crisis.title}</p>
      <p className="text-warroom-amber/80">{crisis.summary}</p>
      <p className="text-xs text-warroom-amber/70">{crisis.effect}</p>
    </div>
  )
}

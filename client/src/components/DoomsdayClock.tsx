import React from 'react'

export function DoomsdayClock({ escalation, maxEscalation = 200 }: { escalation: number; maxEscalation?: number }) {
  const pct = Math.min(100, (escalation / maxEscalation) * 100)
  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className="doomsday-gauge w-16 h-16 flex items-center justify-center"
        style={{ '--doom-pct': `${pct}%` } as React.CSSProperties}
      >
        <div className="w-12 h-12 rounded-full bg-warroom-blue flex items-center justify-center">
          <span className="text-xs font-pixel text-red-400">{Math.round(pct)}%</span>
        </div>
      </div>
      <span className="text-[10px] text-gray-400 font-pixel">DOOM</span>
    </div>
  )
}

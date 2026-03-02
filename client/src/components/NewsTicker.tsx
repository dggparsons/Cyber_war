export function NewsTicker({ news }: { news: Array<{ id: number; message: string }> }) {
  if (!news.length) return null
  // Scale duration with content length so it's always readable (~50px/sec)
  const duration = Math.max(90, news.length * 15)
  return (
    <div className="bg-warroom-slate/70 text-center text-xs text-slate-300">
      <div className="mx-auto max-w-6xl overflow-hidden py-1">
        <div className="animate-marquee whitespace-nowrap" style={{ animationDuration: `${duration}s` }}>
          {news.map((item) => (
            <span key={item.id} className="mx-4">
              ⚡ {item.message}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

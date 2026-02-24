export function NewsTicker({ news }: { news: Array<{ id: number; message: string }> }) {
  if (!news.length) return null
  return (
    <div className="bg-warroom-slate/70 text-center text-xs text-slate-300">
      <div className="mx-auto max-w-6xl overflow-hidden py-1">
        <div className="animate-marquee slow whitespace-nowrap">
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

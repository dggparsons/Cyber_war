import { useState, useRef } from 'react'
import type { FormEvent } from 'react'

export function ChatComposer({ onSend, onTyping }: { onSend: (msg: string) => void; onTyping?: (typing: boolean) => void }) {
  const [value, setValue] = useState('')
  const typingRef = useRef(false)
  const typingTimeout = useRef<ReturnType<typeof setTimeout>>(undefined)

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!value.trim()) return
    onSend(value.trim())
    setValue('')
    if (onTyping && typingRef.current) {
      typingRef.current = false
      onTyping(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value)
    if (onTyping) {
      if (!typingRef.current) {
        typingRef.current = true
        onTyping(true)
      }
      if (typingTimeout.current) clearTimeout(typingTimeout.current)
      typingTimeout.current = setTimeout(() => {
        typingRef.current = false
        onTyping(false)
      }, 2000)
    }
  }

  return (
    <form onSubmit={submit} className="mt-3 flex gap-2">
      <input
        className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm text-slate-100 focus:border-warroom-cyan focus:outline-none"
        placeholder="Type a message..."
        value={value}
        onChange={handleChange}
      />
      <button
        type="submit"
        className="rounded bg-warroom-cyan/20 border border-warroom-cyan/40 px-3 py-2 text-xs font-semibold text-warroom-cyan hover:bg-warroom-cyan/30 transition-colors"
      >
        Send
      </button>
    </form>
  )
}

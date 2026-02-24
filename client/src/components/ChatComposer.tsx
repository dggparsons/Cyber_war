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
    <form onSubmit={submit}>
      <input
        className="mt-3 w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm text-slate-100 focus:border-warroom-cyan focus:outline-none"
        placeholder="Type a message..."
        value={value}
        onChange={handleChange}
      />
    </form>
  )
}

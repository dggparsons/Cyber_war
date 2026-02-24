import { useEffect, useState, useRef, useCallback } from 'react'
import { getTeamSocket } from '../lib/socket'

export type ChatMessage = {
  user_id: number
  display_name: string
  role?: string
  content: string
}

export type TypingUser = {
  user_id: number
  display_name: string
}

export function useChat(enabled = true) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [typingUsers, setTypingUsers] = useState<TypingUser[]>([])
  const typingTimers = useRef<Record<number, ReturnType<typeof setTimeout>>>({})

  useEffect(() => {
    if (!enabled) {
      setMessages([])
      setTypingUsers([])
      return
    }
    const socket = getTeamSocket()
    const historyHandler = (items: ChatMessage[]) => setMessages(items)
    const messageHandler = (item: ChatMessage) => setMessages((prev) => [...prev, item])
    const typingHandler = (data: { user_id: number; display_name: string; typing: boolean }) => {
      if (data.typing) {
        setTypingUsers((prev) => {
          if (prev.some((u) => u.user_id === data.user_id)) return prev
          return [...prev, { user_id: data.user_id, display_name: data.display_name }]
        })
        // Auto-clear after 3s
        if (typingTimers.current[data.user_id]) clearTimeout(typingTimers.current[data.user_id])
        typingTimers.current[data.user_id] = setTimeout(() => {
          setTypingUsers((prev) => prev.filter((u) => u.user_id !== data.user_id))
        }, 3000)
      } else {
        setTypingUsers((prev) => prev.filter((u) => u.user_id !== data.user_id))
      }
    }

    socket.emit('chat:history')
    socket.on('chat:history', historyHandler)
    socket.on('chat:message', messageHandler)
    socket.on('chat:typing', typingHandler)

    return () => {
      socket.off('chat:history', historyHandler)
      socket.off('chat:message', messageHandler)
      socket.off('chat:typing', typingHandler)
      Object.values(typingTimers.current).forEach(clearTimeout)
    }
  }, [enabled])

  const sendMessage = useCallback((content: string) => {
    if (!enabled) return
    const socket = getTeamSocket()
    socket.emit('chat:message', { content })
  }, [enabled])

  const sendTyping = useCallback((typing: boolean) => {
    if (!enabled) return
    const socket = getTeamSocket()
    socket.emit('chat:typing', { typing })
  }, [enabled])

  return { messages, sendMessage, typingUsers, sendTyping }
}

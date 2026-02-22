import { useEffect, useState } from 'react'
import { getTeamSocket } from '../lib/socket'

export type ChatMessage = {
  user_id: number
  display_name: string
  content: string
}

export function useChat(enabled = true) {
  const [messages, setMessages] = useState<ChatMessage[]>([])

  useEffect(() => {
    if (!enabled) {
      setMessages([])
      return
    }
    const socket = getTeamSocket()
    const historyHandler = (items: ChatMessage[]) => setMessages(items)
    const messageHandler = (item: ChatMessage) => setMessages((prev) => [...prev, item])

    socket.emit('chat:history')
    socket.on('chat:history', historyHandler)
    socket.on('chat:message', messageHandler)

    return () => {
      socket.off('chat:history', historyHandler)
      socket.off('chat:message', messageHandler)
    }
  }, [enabled])

  const sendMessage = (content: string) => {
    if (!enabled) return
    const socket = getTeamSocket()
    socket.emit('chat:message', { content })
  }

  return { messages, sendMessage }
}

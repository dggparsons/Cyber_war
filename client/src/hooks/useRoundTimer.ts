import { useEffect, useRef, useState } from 'react'
import type { TimerPayload } from '../lib/api'
import { getGlobalSocket } from '../lib/socket'

export type RoundTimer = TimerPayload

export function useRoundTimer(initial: RoundTimer) {
  const [timer, setTimer] = useState<RoundTimer>(initial)
  const updateRef = useRef<number>(Date.now())

  useEffect(() => {
    setTimer(initial)
    updateRef.current = Date.now()
  }, [initial.round, initial.remaining, initial.duration, initial.state])

  useEffect(() => {
    const socket = getGlobalSocket()
    const tickHandler = (payload: { round_id?: number; round?: number; remaining: number; duration?: number; state?: RoundTimer['state']; server_time?: string }) => {
      updateRef.current = Date.now()
      setTimer((prev) => ({
        round: payload.round_id ?? payload.round ?? prev.round,
        remaining: payload.remaining,
        duration: payload.duration ?? prev.duration,
        state: payload.state ?? prev.state,
        server_time: payload.server_time ?? prev.server_time,
      }))
    }
    const startedHandler = (payload: { round: number }) =>
      setTimer((prev) => ({
        round: payload.round,
        remaining: prev.duration,
        duration: prev.duration,
        state: 'running',
      }))
    const pausedHandler = (payload: TimerPayload) =>
      setTimer({
        round: payload.round,
        remaining: payload.remaining,
        duration: payload.duration,
        state: 'paused',
      })
    const resumedHandler = (payload: TimerPayload) =>
      setTimer({
        round: payload.round,
        remaining: payload.remaining,
        duration: payload.duration,
        state: 'running',
      })
    const endHandler = (payload: { round_id?: number; round?: number; state?: RoundTimer['state'] }) =>
      setTimer((prev) => ({
        round: payload.round_id ?? payload.round ?? prev.round,
        remaining: 0,
        duration: prev.duration,
        state: payload.state ?? 'complete',
      }))
    socket.on('round:tick', tickHandler)
    socket.on('round:started', startedHandler)
    socket.on('round:paused', pausedHandler)
    socket.on('round:resumed', resumedHandler)
    socket.on('round:timer_end', endHandler)

    return () => {
      socket.off('round:tick', tickHandler)
      socket.off('round:started', startedHandler)
      socket.off('round:paused', pausedHandler)
      socket.off('round:resumed', resumedHandler)
      socket.off('round:timer_end', endHandler)
    }
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setTimer((prev) => {
        if (prev.state !== 'running') return prev
        const now = Date.now()
        const elapsed = now - updateRef.current
        if (elapsed < 1000) return prev
        const steps = Math.floor(elapsed / 1000)
        updateRef.current += steps * 1000
        const remaining = Math.max(0, prev.remaining - steps)
        if (remaining === prev.remaining) return prev
        return { ...prev, remaining }
      })
    }, 250)
    return () => clearInterval(interval)
  }, [])

  return timer
}

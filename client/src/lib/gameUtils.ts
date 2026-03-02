import type { RoundTimer } from '../hooks/useRoundTimer'
import type { GlobalStatePayload } from './api'
export type { GlobalStatePayload } from './api'

export const SLOT_IDS = [1]

export const DEFAULT_GLOBAL_STATE: GlobalStatePayload = {
  nuke_unlocked: false,
  doom_triggered: false,
  doom_message: null,
  active_crisis: null,
  last_crisis_at: null,
}

export const NATION_COLORS = [
  '#ef4444', '#38bdf8', '#22c55e', '#eab308', '#a855f7',
  '#f97316', '#ec4899', '#14b8a6', '#6366f1', '#f43f5e', '#84cc16',
]

export function getCategoryColor(category: string): string {
  switch (category) {
    case 'de_escalation': return '#22c55e'
    case 'status_quo': return '#f8fafc'
    case 'posturing': return '#eab308'
    case 'non_violent': return '#f97316'
    case 'violent': return '#ef4444'
    case 'nuclear': return '#a855f7'
    default: return '#f8fafc'
  }
}

export function formatTimerDisplay(timer: RoundTimer): string {
  if (timer.state === 'paused') return 'PAUSED'
  const mins = Math.floor(timer.remaining / 60)
  const secs = timer.remaining % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

export type Proposal = {
  id: number
  slot: number
  action_code: string
  status: string
  target_team_id?: number
  false_flag_target_team_id?: number | null
  vetoed_by_user_id?: number | null
  vetoed_reason?: string | null
  votes: Array<{ user_id: number; value: number }>
}

export type GameState = {
  team: {
    id: number
    nation_name: string
    nation_code: string
    role: string
    team_type?: string | null
    seat_cap: number
  }
  advisors: Array<{ name: string; mood: string; hint: string; avatar?: string }>
  action_slots: Array<{ slot: number }>
  chat_sample: string[]
  narrative: string
  round: { id: number; number: number }
  intel_drops: Array<{ id: number; title: string; description: string; reward: string; status: string }>
  communications_hint: string
  briefing: {
    title: string
    summary: string
    allies: string[]
    threats: string[]
    consequences: string
  }
  timer: import('./api').TimerPayload
  lifelines: Array<{ id: number; lifeline_type: string; remaining_uses: number; awarded_for?: string | null }>
  alliances: Array<{ team_a_id: number; team_b_id: number; status: string; formed_at: string | null }>
  proposals: Proposal[]
  global: GlobalStatePayload
  roster?: Array<{ id: number; display_name: string; role: string; is_captain: boolean }>
}

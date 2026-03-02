const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? `http://${window.location.hostname}:5050`

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!res.ok) {
    const message = await res.text()
    throw new ApiError(message || 'Request failed', res.status)
  }

  if (res.status === 204) return null
  return res.json()
}

export type TimerState = 'idle' | 'running' | 'paused' | 'complete'

export type TimerPayload = {
  round: number
  remaining: number
  duration: number
  state: TimerState
  server_time?: string
}

export type CrisisInfo = {
  code: string
  title: string
  summary: string
  effect: string
  applied_at?: string
}

export type GlobalStatePayload = {
  nuke_unlocked: boolean
  doom_triggered: boolean
  doom_message?: string | null
  active_crisis?: CrisisInfo | null
  last_crisis_at?: string | null
  total_escalation?: number
  escalation_thresholds?: number[]
}

type GameStateResponse = {
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
  timer: TimerPayload
  lifelines: Array<{ id: number; lifeline_type: string; remaining_uses: number; awarded_for?: string | null }>
  alliances: Array<{ team_a_id: number; team_b_id: number; status: string; formed_at: string | null }>
  proposals: Array<{
    id: number
    slot: number
    action_code: string
    status: string
    target_team_id?: number
    false_flag_target_team_id?: number | null
    vetoed_by_user_id?: number | null
    vetoed_reason?: string | null
    votes: Array<{ user_id: number; value: number }>
  }>
  global: GlobalStatePayload
}

export type CyberImpactEntry = {
  round: number
  actor: string
  target: string
  action: string
  success: boolean
}

export type LeaderboardResponse = {
  entries: Array<{ team_id: number; nation_name: string; score: number; delta_from_baseline: number; escalation: number }>
  escalation_series: Record<string, Array<{ round: number; score: number }>>
  cyber_impact?: CyberImpactEntry[]
  timer: TimerPayload
  global?: GlobalStatePayload
}

export type ActionDefinition = {
  code: string
  name: string
  category: string
  escalation: number
  description: string
  target_required: boolean
}

export type RevealData = {
  ai_models: Array<{
    model_name: string
    nation_code?: string
    first_violent_round: number | null
    launched_nukes: boolean
    avg_escalation: number
    reasoning_excerpts?: Array<{ round: number; action: string; reasoning: string }>
  }>
  human_vs_ai: { human_outcome: number; ai_outcome: number; rounds?: number }
  human_escalation_series?: Array<{ round: number; avg_outcome: number }>
  ai_escalation_series?: Record<string, Array<{ round: number; escalation: number; outcome: number }>>
  ai_avg_by_round?: Array<{ round: number; avg_escalation: number; avg_outcome: number }>
  ai_decisions?: Array<{ round: number; nation_code: string; action_code: string; target?: string; success: boolean; reasoning?: string }>
  ai_run?: { id: number; model_name: string; final_escalation?: number; doom_triggered?: boolean; completed_at?: string }
}

export async function captainOverride(proposal_id: number): Promise<any> {
  return apiFetch('/api/game/proposals/captain-override', {
    method: 'POST',
    body: JSON.stringify({ proposal_id }),
  })
}

export type HistoryEntry = {
  id: number
  round: number
  action_code: string
  success: boolean
  actor?: string | null
  target?: string | null
  slot: number
  created_at?: string | null
}

export type ProposalPreview = {
  team_id: number
  nation_name: string
  proposals: Array<{
    id: number
    slot: number
    action_code: string
    status: string
    target_team_id?: number
    votes: number
    vetoed_by_user_id?: number | null
  }>
}

export async function fetchGameState(): Promise<GameStateResponse> {
  return apiFetch('/api/game/state', { method: 'GET' })
}

export type SessionResponse = {
  authenticated: boolean
  user?: { id: number; display_name: string; email: string; team_id: number | null; role: string; is_captain: boolean }
  session_token?: string
}

export async function fetchSession(): Promise<SessionResponse> {
  return apiFetch('/api/auth/me', { method: 'GET' })
}
export async function fetchLeaderboard(): Promise<LeaderboardResponse> {
  return apiFetch('/api/game/leaderboard', { method: 'GET' })
}

export async function fetchActions(): Promise<ActionDefinition[]> {
  return apiFetch('/api/game/actions', { method: 'GET' })
}

export async function submitProposal(slot: number, action_code: string, target_team_id?: number): Promise<any> {
  return apiFetch('/api/game/proposals', {
    method: 'POST',
    body: JSON.stringify({ slot, action_code, target_team_id }),
  })
}

export async function castVote(proposal_id: number, value: 1 | -1): Promise<any> {
  return apiFetch('/api/game/votes', {
    method: 'POST',
    body: JSON.stringify({ proposal_id, value }),
  })
}

export async function fetchRevealData(): Promise<RevealData> {
  return apiFetch('/api/reveal/', { method: 'GET' })
}

export async function registerUser(displayName: string, email: string): Promise<{ password: string }> {
  return apiFetch('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ display_name: displayName, email }),
  })
}

export async function loginUser(email: string, password: string): Promise<void> {
  await apiFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function joinWithCode(display_name: string, join_code: string) {
  return apiFetch('/api/auth/join', {
    method: 'POST',
    body: JSON.stringify({ display_name, join_code }),
  })
}

export async function adminStartRound() {
  return apiFetch('/api/admin/rounds/start', { method: 'POST' })
}

export async function adminAdvanceRound() {
  return apiFetch('/api/admin/rounds/advance', { method: 'POST' })
}

export async function adminResetRounds() {
  return apiFetch('/api/admin/rounds/reset', { method: 'POST' })
}

export async function adminListRounds() {
  return apiFetch('/api/admin/rounds', { method: 'GET' })
}

export async function adminPauseTimer() {
  return apiFetch('/api/admin/rounds/pause', { method: 'POST' })
}

export async function adminResumeTimer() {
  return apiFetch('/api/admin/rounds/resume', { method: 'POST' })
}

export async function adminFetchStatus() {
  return apiFetch('/api/admin/status', { method: 'GET' })
}

export async function adminToggleNukes(unlocked: boolean) {
  return apiFetch('/api/admin/nukes/toggle', {
    method: 'POST',
    body: JSON.stringify({ unlocked }),
  })
}

export async function adminInjectCrisis(code: string) {
  return apiFetch('/api/admin/crisis/inject', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export async function adminClearCrisis() {
  return apiFetch('/api/admin/crisis/clear', { method: 'POST' })
}

export async function adminFullReset() {
  return apiFetch('/api/admin/full-reset', { method: 'POST' })
}

export async function adminRerunNarrative(): Promise<{ narrative: string }> {
  return apiFetch('/api/admin/narrative/rerun', { method: 'POST' })
}

export async function fetchDiplomacyChannels() {
  return apiFetch('/api/diplomacy/', { method: 'GET' })
}

export async function startDiplomacy(target_team_id: number) {
  return apiFetch('/api/diplomacy/start', {
    method: 'POST',
    body: JSON.stringify({ target_team_id }),
  })
}

export async function sendDiplomacyMessage(channel_id: number, content: string) {
  return apiFetch('/api/diplomacy/send', {
    method: 'POST',
    body: JSON.stringify({ channel_id, content }),
  })
}

export async function respondDiplomacy(channel_id: number, action: 'accept' | 'decline') {
  return apiFetch('/api/diplomacy/respond', {
    method: 'POST',
    body: JSON.stringify({ channel_id, action }),
  })
}

export async function fetchNews() {
  return apiFetch('/api/game/news', { method: 'GET' })
}

export async function fetchHistory(limit = 20): Promise<{ entries: HistoryEntry[] }> {
  return apiFetch(`/api/game/history?limit=${limit}`, { method: 'GET' })
}

export async function solveIntel(intel_id: number, answer: string) {
  return apiFetch('/api/game/intel/solve', {
    method: 'POST',
    body: JSON.stringify({ intel_id, answer }),
  })
}

export async function applyFalseFlag(proposal_id: number, blame_team_id: number) {
  return apiFetch('/api/game/lifelines/false_flag', {
    method: 'POST',
    body: JSON.stringify({ proposal_id, blame_team_id }),
  })
}

export async function fetchProposalPreview() {
  return apiFetch('/api/game/proposals/preview', { method: 'GET' })
}

export async function vetoProposal(proposal_id: number, reason?: string) {
  return apiFetch('/api/game/proposals/veto', {
    method: 'POST',
    body: JSON.stringify({ proposal_id, reason }),
  })
}

// Mega Challenge
export type MegaChallengeData = {
  active: boolean
  id?: number
  description?: string
  reward_tiers?: number[]
  solved_by?: Array<{ team_id: number; position: number; reward: number }>
  already_solved?: boolean
}

export async function fetchMegaChallenge(): Promise<MegaChallengeData> {
  return apiFetch('/api/game/mega-challenge', { method: 'GET' })
}

export async function solveMegaChallenge(answer: string) {
  return apiFetch('/api/game/mega-challenge/solve', {
    method: 'POST',
    body: JSON.stringify({ answer }),
  })
}

// Phone-a-Friend
export async function usePhoneAFriend(): Promise<{ hint: { team_name: string; action_name: string; slot: number } }> {
  return apiFetch('/api/game/lifelines/phone-a-friend', { method: 'POST' })
}

// Admin: Mega Challenge
export async function adminCreateMegaChallenge(description: string, solution: string, reward_tiers?: number[]) {
  return apiFetch('/api/admin/mega-challenge', {
    method: 'POST',
    body: JSON.stringify({ description, solution, reward_tiers }),
  })
}

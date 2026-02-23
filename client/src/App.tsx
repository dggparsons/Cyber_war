import React, { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import type { FormEvent } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'
import './App.css'
import {
  fetchGameState,
  fetchSession,
  fetchLeaderboard,
  fetchRevealData,
  fetchActions,
  submitProposal,
  castVote,
  registerUser,
  loginUser,
  joinWithCode,
  ApiError,
  type LeaderboardResponse,
  type RevealData,
  type ActionDefinition,
  type GlobalStatePayload,
  type CrisisInfo,
  adminAdvanceRound,
  adminListRounds,
  adminResetRounds,
  adminStartRound,
  adminPauseTimer,
  adminResumeTimer,
  adminFetchStatus,
  adminToggleNukes,
  adminInjectCrisis,
  adminClearCrisis,
  fetchDiplomacyChannels,
  startDiplomacy,
  sendDiplomacyMessage,
  fetchNews,
  solveIntel,
  applyFalseFlag,
  fetchHistory,
  fetchProposalPreview,
  vetoProposal,
  type HistoryEntry,
  type ProposalPreview,
} from './lib/api'
import { useChat } from './hooks/useChat'
import { useRoundTimer, type RoundTimer } from './hooks/useRoundTimer'
import { getTeamSocket, getGlobalSocket } from './lib/socket'

class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: string}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: '' };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error: error.message };
  }
  render() {
    if (this.state.hasError) {
      return <div className="min-h-screen bg-warroom-blue flex items-center justify-center text-red-400 p-8">
        <div className="text-center"><h1 className="text-2xl font-pixel mb-4">SYSTEM ERROR</h1><p>{this.state.error}</p><button onClick={() => this.setState({hasError: false, error: ''})} className="mt-4 px-4 py-2 bg-warroom-cyan text-black rounded">Retry</button></div>
      </div>;
    }
    return this.props.children;
  }
}

function getCategoryColor(category: string): string {
  switch(category) {
    case 'de_escalation': return '#22c55e'; // green
    case 'status_quo': return '#f8fafc'; // white
    case 'posturing': return '#eab308'; // yellow
    case 'non_violent': return '#f97316'; // orange
    case 'violent': return '#ef4444'; // red
    case 'nuclear': return '#a855f7'; // purple
    default: return '#f8fafc';
  }
}

const viewMode = new URLSearchParams(window.location.search).get('view') ?? 'player'
const SLOT_IDS = [1, 2, 3]
const DEFAULT_GLOBAL_STATE: GlobalStatePayload = {
  nuke_unlocked: false,
  doom_triggered: false,
  doom_message: null,
  active_crisis: null,
  last_crisis_at: null,
}

type Proposal = {
  id: number
  slot: number
  action_code: string
  status: string
  target_team_id?: number
  false_flag_target_team_id?: number | null
  votes: Array<{ user_id: number; value: number }>
}

type GameState = Awaited<ReturnType<typeof fetchGameState>>

function ChatComposer({ onSend }: { onSend: (msg: string) => void }) {
  const [value, setValue] = useState('')

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!value.trim()) return
    onSend(value.trim())
    setValue('')
  }

  return (
    <form onSubmit={submit}>
      <input
        className="mt-3 w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm text-slate-100 focus:border-warroom-cyan focus:outline-none"
        placeholder="Type a message..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
    </form>
  )
}

function AuthPanel({ onAuthenticated, errorMessage }: { onAuthenticated: () => void; errorMessage: string | null }) {
  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [joinCode, setJoinCode] = useState('')
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [message, setMessage] = useState<string | null>(errorMessage)

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    try {
      if (joinCode.trim()) {
        const result = await joinWithCode(registerName, joinCode)
        setGeneratedPassword(result.password)
        setLoginEmail(result.user.email)
        setLoginPassword(result.password)
        setMessage('Join code accepted. Password generated below—log in to continue.')
      } else {
        const result = await registerUser(registerName, registerEmail)
        setGeneratedPassword(result.password)
        setLoginEmail(registerEmail)
        setLoginPassword(result.password)
        setMessage('Registration successful. Use the generated password to log in.')
      }
    } catch (err) {
      console.error(err)
      setMessage('Registration failed. Check your join code or email.')
    }
  }

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await loginUser(loginEmail, loginPassword)
      setMessage(null)
      onAuthenticated()
    } catch (err) {
      console.error(err)
      setMessage('Login failed. Check your credentials.')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-warroom-blue px-4 text-slate-100">
      <div className="grid w-full max-w-3xl gap-6 rounded-lg border border-slate-700 bg-slate-900/70 p-6 shadow-lg shadow-warroom-cyan/10 md:grid-cols-2">
        <div>
          <h2 className="font-pixel text-warroom-cyan">Register</h2>
          <p className="text-xs text-slate-400">Generate a random password and copy it to log in.</p>
          <form className="mt-3 space-y-3" onSubmit={handleRegister}>
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Display name" value={registerName} onChange={(e) => setRegisterName(e.target.value)} required />
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Email (or leave blank if using join code)" value={registerEmail} onChange={(e) => setRegisterEmail(e.target.value)} disabled={Boolean(joinCode.trim())} required={!joinCode.trim()} />
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Join code (optional)" value={joinCode} onChange={(e) => setJoinCode(e.target.value)} />
            <button className="w-full rounded border border-slate-600 bg-warroom-cyan/20 py-2 text-xs font-bold tracking-wide text-warroom-cyan" type="submit">Register & Generate Password</button>
          </form>
          {generatedPassword && (
            <div className="mt-3 rounded border border-slate-600 bg-warroom-blue/50 p-3 text-xs">
              <p className="text-slate-300">Generated Password:</p>
              <p className="font-mono text-warroom-amber">{generatedPassword}</p>
            </div>
          )}
        </div>

        <div>
          <h2 className="font-pixel text-warroom-cyan">Login</h2>
          <p className="text-xs text-slate-400">Use the generated password (or one from the GM) to sign in.</p>
          <form className="mt-3 space-y-3" onSubmit={handleLogin}>
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Email" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} required />
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Password" type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} required />
            <button className="w-full rounded border border-slate-600 bg-warroom-amber/30 py-2 text-xs font-bold tracking-wide text-warroom-amber" type="submit">Login</button>
          </form>
          {message && <p className="mt-3 text-xs text-slate-300">{message}</p>}
        </div>
      </div>
    </div>
  )
}

function App() {
  const [data, setData] = useState<GameState | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [globalState, setGlobalState] = useState<GlobalStatePayload | null>(null)
  const chatEnabled = !authRequired && Boolean(data?.team?.id)
  const { messages, sendMessage } = useChat(chatEnabled)
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null)
  const [revealData, setRevealData] = useState<RevealData | null>(null)
  const [actions, setActions] = useState<ActionDefinition[]>([])
  const [selection, setSelection] = useState<Record<number, string>>({})
  const [targets, setTargets] = useState<Record<number, number>>({})
  const [timerSeed, setTimerSeed] = useState<RoundTimer>({ round: 1, remaining: 0, duration: 360, state: 'idle' })
  const [isBriefingOpen, setIsBriefingOpen] = useState(false)
  const [isNationsOpen, setIsNationsOpen] = useState(false)
  const [diplomacyChannels, setDiplomacyChannels] = useState<any[]>([])
  const [diplomacyDrafts, setDiplomacyDrafts] = useState<Record<number, string>>({})
  const [diplomacyTarget, setDiplomacyTarget] = useState<number | ''>('')
  const [newsFeed, setNewsFeed] = useState<Array<{ id: number; message: string }>>([])
  const [crisisFlash, setCrisisFlash] = useState<CrisisInfo | null>(null)
  const [historyEntries, setHistoryEntries] = useState<HistoryEntry[]>([])
  const [shouldShowReveal, setShouldShowReveal] = useState(false)
  const [intelAnswers, setIntelAnswers] = useState<Record<number, string>>({})
  const [falseFlagTargets, setFalseFlagTargets] = useState<Record<number, number | ''>>({})
  const [escalationFlash, setEscalationFlash] = useState<{ threshold: number; severity: string; total: number } | null>(null)
  const [previewData, setPreviewData] = useState<{ round: number; limit: number; vetoes_used: number; teams: ProposalPreview[] } | null>(null)
  const [connected, setConnected] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const isUN = Boolean(data?.team && ((data.team.team_type ?? '').toLowerCase() === 'un' || data.team.nation_code === 'UN'))
  const timer = useRoundTimer(timerSeed)
  const effectiveGlobal = globalState ?? data?.global ?? leaderboard?.global ?? DEFAULT_GLOBAL_STATE
  const playCue = useCallback((frequency = 420, duration = 0.25) => {
    if (typeof window === 'undefined') return
    try {
      let ctx = audioCtxRef.current
      if (!ctx) {
        ctx = new AudioContext()
        audioCtxRef.current = ctx
      }
      if (ctx.state === 'suspended') {
        ctx.resume()
      }
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()
      oscillator.type = 'triangle'
      oscillator.frequency.value = frequency
      oscillator.connect(gain)
      gain.connect(ctx.destination)
      gain.gain.setValueAtTime(0.15, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration)
      oscillator.start()
      oscillator.stop(ctx.currentTime + duration)
    } catch (err) {
      console.warn('Audio cue error', err)
    }
  }, [])

  const refreshPreview = useCallback(async () => {
    if (!isUN) {
      setPreviewData(null)
      return
    }
    try {
      const preview = await fetchProposalPreview()
      setPreviewData(preview)
    } catch (err) {
      console.error(err)
    }
  }, [isUN])

  const loadGameState = useCallback(async () => {
    try {
      setStatus('loading')
      const gameState = await fetchGameState()
      setData(gameState)
      setGlobalState(gameState.global ?? DEFAULT_GLOBAL_STATE)
      setStatus('ready')
      setAuthRequired(false)
      setTimerSeed(gameState.timer)
      setIsBriefingOpen(true)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setAuthRequired(true)
        setStatus('ready')
        setError(null)
      } else {
        console.error(err)
        setError('Unable to load game data. Try again later.')
        setStatus('error')
      }
    }
  }, [])

  const handleAuthenticated = useCallback(() => {
    setAuthRequired(false)
    setStatus('loading')
    loadGameState()
  }, [loadGameState])

  useEffect(() => {
    if (viewMode !== 'player') {
      setStatus('ready')
      return
    }
    let cancelled = false
    const bootstrap = async () => {
      try {
        const session = await fetchSession()
        if (cancelled) return
        if (session.authenticated) {
          setAuthRequired(false)
          loadGameState()
        } else {
          setAuthRequired(true)
          setStatus('ready')
        }
      } catch (err) {
        if (cancelled) return
        setAuthRequired(true)
        setStatus('ready')
      }
    }
    bootstrap()
    return () => {
      cancelled = true
    }
  }, [loadGameState, viewMode])

  useEffect(() => {
    if (viewMode !== 'player' || authRequired || !data) return
    let cancelled = false
    const loadActions = async () => {
      try {
        const list = await fetchActions()
        if (!cancelled) setActions(list)
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setAuthRequired(true)
          return
        }
        console.error(err)
      }
    }
    loadActions()
    return () => {
      cancelled = true
    }
  }, [authRequired, data, viewMode])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const lb = await fetchLeaderboard()
        if (!cancelled) {
          setLeaderboard(lb)
          if (lb.timer) setTimerSeed(lb.timer)
          if (lb.global) {
            setGlobalState((prev) => ({ ...(prev ?? DEFAULT_GLOBAL_STATE), ...lb.global }))
          }
        }
      } catch (err) {
        console.error(err)
      }
    }
    load()
    const interval = setInterval(load, 10000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    if (viewMode === 'gm' || effectiveGlobal.doom_triggered) {
      setShouldShowReveal(true)
    }
  }, [viewMode, effectiveGlobal.doom_triggered])

  useEffect(() => {
    if (!shouldShowReveal) return
    let cancelled = false
    ;(async () => {
      try {
        const data = await fetchRevealData()
        if (!cancelled) setRevealData(data)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          return
        }
        console.error(err)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [shouldShowReveal])

  useEffect(() => {
    if (viewMode !== 'player' || authRequired || !data?.team?.id) {
      setDiplomacyChannels([])
      return
    }
    let cancelled = false
    const loadDiplomacy = async () => {
      try {
        const channels = await fetchDiplomacyChannels()
        if (!cancelled) setDiplomacyChannels(channels)
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setAuthRequired(true)
          return
        }
        console.error(err)
      }
    }
    loadDiplomacy()
    const socket = getTeamSocket()
    const handler = (payload: any) => {
      setDiplomacyChannels((prev) => {
        const copy = prev.map((channel) =>
          channel.channel_id === payload.channel_id
            ? {
                ...channel,
                messages: [...channel.messages, { id: payload.id ?? Date.now(), content: payload.content, user_id: payload.team_id, sent_at: payload.sent_at, display_name: payload.display_name }],
              }
            : channel,
        )
        return copy.length ? copy : prev
      })
    }
    socket.on('diplomacy:message', handler)
    return () => {
      cancelled = true
      socket.off('diplomacy:message', handler)
    }
  }, [authRequired, data?.team?.id, viewMode])

  useEffect(() => {
    if (!isUN) {
      setPreviewData(null)
      return
    }
    let cancelled = false
    const load = async () => {
      try {
        const preview = await fetchProposalPreview()
        if (!cancelled) setPreviewData(preview)
      } catch (err) {
        console.error(err)
      }
    }
    load()
    const interval = setInterval(load, 7000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [isUN, viewMode])

  useEffect(() => {
    let cancelled = false
    const loadHistory = async () => {
      try {
        const response = await fetchHistory(25)
        if (!cancelled) setHistoryEntries(response.entries)
      } catch (err) {
        console.error(err)
      }
    }
    const canFetch = viewMode === 'spectator' || (viewMode === 'player' && !authRequired)
    if (canFetch) {
      loadHistory()
      const interval = setInterval(loadHistory, 10000)
      return () => {
        cancelled = true
        clearInterval(interval)
      }
    }
    return () => {
      cancelled = true
    }
  }, [authRequired, viewMode])

  useEffect(() => {
    let cancelled = false
    const loadNews = async () => {
      try {
        const news = await fetchNews()
        if (!cancelled) setNewsFeed(news)
      } catch (err) {
        console.error(err)
      }
    }
    loadNews()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (viewMode === 'player' && authRequired) return
    const socket = getGlobalSocket()
    const nukeHandler = (payload: { nuke_unlocked: boolean }) =>
      setGlobalState((prev) => ({ ...(prev ?? DEFAULT_GLOBAL_STATE), ...payload }))
    const doomHandler = (payload: { doom_triggered: boolean; message?: string }) => {
      setGlobalState((prev) => ({
        ...(prev ?? DEFAULT_GLOBAL_STATE),
        doom_triggered: payload.doom_triggered,
        doom_message: payload.message ?? prev?.doom_message ?? null,
      }))
      if (payload.doom_triggered) playCue(180, 0.5)
    }
    const crisisHandler = (payload: CrisisInfo) => {
      setGlobalState((prev) => ({ ...(prev ?? DEFAULT_GLOBAL_STATE), active_crisis: payload }))
      setCrisisFlash(payload)
      playCue(320, 0.3)
    }
    const crisisClearedHandler = () =>
      setGlobalState((prev) => (prev ? { ...prev, active_crisis: null } : prev))
    const newsHandler = (payload: { id: number; message: string }) => {
      setNewsFeed((prev) => {
        const filtered = prev.filter((item) => item.id !== payload.id)
        return [{ id: payload.id, message: payload.message }, ...filtered].slice(0, 30)
      })
    }
    const escalationHandler = (payload: { threshold: number; total: number; severity: string }) => {
      setGlobalState((prev) => ({ ...(prev ?? DEFAULT_GLOBAL_STATE), total_escalation: payload.total }))
      setEscalationFlash(payload)
      playCue(260 + payload.threshold, 0.35)
    }
    socket.on('game:nuke_state', nukeHandler)
    socket.on('game:over', doomHandler)
    socket.on('crisis:injected', crisisHandler)
    socket.on('crisis:cleared', crisisClearedHandler)
    socket.on('news:event', newsHandler)
    socket.on('escalation:threshold', escalationHandler)
    return () => {
      socket.off('game:nuke_state', nukeHandler)
      socket.off('game:over', doomHandler)
      socket.off('crisis:injected', crisisHandler)
      socket.off('crisis:cleared', crisisClearedHandler)
      socket.off('news:event', newsHandler)
      socket.off('escalation:threshold', escalationHandler)
    }
  }, [authRequired, playCue, viewMode])

  useEffect(() => {
    if (viewMode !== 'player' || authRequired || !data?.team?.id) return
    const socket = getTeamSocket()
    const autoLockHandler = (payload: { proposals: Proposal[] }) => {
      setData((prev) => (prev ? { ...prev, proposals: payload.proposals } : prev))
    }
    const vetoHandler = (payload: { proposal_id: number; status: string; vetoed_by_user_id?: number; vetoed_reason?: string }) => {
      setData((prev) =>
        prev
          ? {
              ...prev,
              proposals: prev.proposals.map((proposal) =>
                proposal.id === payload.proposal_id
                  ? {
                      ...proposal,
                      status: payload.status,
                      vetoed_by_user_id: payload.vetoed_by_user_id ?? null,
                      vetoed_reason: payload.vetoed_reason ?? null,
                    }
                  : proposal,
              ),
            }
          : prev,
      )
      if (isUN) {
        refreshPreview()
      }
    }
    socket.on('proposals:auto_locked', autoLockHandler)
    socket.on('proposal:vetoed', vetoHandler)
    return () => {
      socket.off('proposals:auto_locked', autoLockHandler)
      socket.off('proposal:vetoed', vetoHandler)
    }
  }, [authRequired, data?.team?.id, viewMode, isUN, refreshPreview])

  useEffect(() => {
    if (!crisisFlash) return
    const timeout = setTimeout(() => setCrisisFlash(null), 6000)
    return () => clearTimeout(timeout)
  }, [crisisFlash])

  useEffect(() => {
    if (!escalationFlash) return
    const timeout = setTimeout(() => setEscalationFlash(null), 5000)
    return () => clearTimeout(timeout)
  }, [escalationFlash])

  useEffect(() => {
    const socket = getGlobalSocket()
    setConnected(socket.connected)
    const onConnect = () => setConnected(true)
    const onDisconnect = () => setConnected(false)
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
    }
  }, [])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const timerDisplay = useMemo(() => formatTimerDisplay(timer), [timer])
  const timerProgress = useMemo(() => {
    if (!timer.duration) return 0
    const ratio = timer.remaining / timer.duration
    return Math.max(0, Math.min(1, ratio))
  }, [timer.remaining, timer.duration])

  const nukeUnlocked = effectiveGlobal.nuke_unlocked
  const availableActions = useMemo(
    () => actions.filter((action) => nukeUnlocked || action.category !== 'nuclear'),
    [actions, nukeUnlocked],
  )

  if (viewMode === 'spectator') {
    return <SpectatorView leaderboard={leaderboard} timer={timer} reveal={revealData} news={newsFeed} global={effectiveGlobal} />
  }

  if (viewMode === 'gm') {
    return <AdminPanel />
  }

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-warroom-blue text-slate-100">
        <p className="font-pixel tracking-widest text-warroom-cyan">BOOTING WAR ROOM...</p>
      </div>
    )
  }

  if (status === 'error' || !data) {
    if (authRequired) {
      return <AuthPanel onAuthenticated={handleAuthenticated} errorMessage={error} />
    }
    return (
      <div className="flex min-h-screen items-center justify-center bg-warroom-blue text-center text-slate-100">
        <div>
          <p className="font-pixel text-warroom-amber">CONNECTION LOST</p>
          <p className="mt-2 max-w-sm text-sm text-slate-300">{error}</p>
        </div>
      </div>
    )
  }

  const teamOptions = leaderboard?.entries.filter((entry) => entry.team_id !== data.team.id) ?? []
  const lifelines = data.lifelines ?? []
  const falseFlagCount = lifelines.find((item) => item.lifeline_type === 'false_flag')?.remaining_uses ?? 0
  const totalEscalation = effectiveGlobal.total_escalation ?? 0
  const nextThreshold =
    (effectiveGlobal.escalation_thresholds ?? []).find((value) => value > totalEscalation) ??
    null
  const vetoesUsed = previewData?.vetoes_used ?? 0
  const vetoLimit = previewData?.limit ?? 1
  const vetoLimitReached = vetoesUsed >= vetoLimit
  const doomActive = effectiveGlobal.doom_triggered
  const activeCrisis = effectiveGlobal.active_crisis ?? null
  const doomMessage = effectiveGlobal.doom_message ?? 'A catastrophic strike ended the scenario.'

  const handleSelectionChange = (slot: number, value: string) => setSelection((prev) => ({ ...prev, [slot]: value }))
  const handleTargetChange = (slot: number, value: number) => setTargets((prev) => ({ ...prev, [slot]: value }))

  const actionName = (code: string) => actions.find((a) => a.code === code)?.name ?? code

  const handleSubmitProposal = async (slot: number) => {
    if (doomActive) return
    const actionCode = selection[slot]
    if (!actionCode) return
    const action = actions.find((a) => a.code === actionCode)
    const targetId = targets[slot]
    if (action?.target_required && !targetId) {
      alert('This action requires selecting a target nation.')
      return
    }
    try {
      await submitProposal(slot, actionCode, targetId)
      setSelection((prev) => ({ ...prev, [slot]: '' }))
      await loadGameState()
    } catch (err) {
      console.error(err)
      alert('Failed to submit action.')
    }
  }

  const handleVote = async (proposalId: number, value: 1 | -1) => {
    if (doomActive) return
    try {
      await castVote(proposalId, value)
      await loadGameState()
    } catch (err) {
      console.error(err)
      alert('Failed to register vote.')
    }
  }

  const handleStartDiplomacy = async () => {
    if (!diplomacyTarget) return
    try {
      await startDiplomacy(Number(diplomacyTarget))
      setDiplomacyTarget('')
      const channels = await fetchDiplomacyChannels()
      setDiplomacyChannels(channels)
    } catch (err) {
      console.error(err)
      alert('Failed to start diplomacy channel.')
    }
  }

  const handleSendDiplomacy = async (channelId: number) => {
    const content = diplomacyDrafts[channelId]
    if (!content) return
    try {
      await sendDiplomacyMessage(channelId, content)
      setDiplomacyDrafts((prev) => ({ ...prev, [channelId]: '' }))
    } catch (err) {
      console.error(err)
      alert('Failed to send diplomacy message.')
    }
  }

  const handleIntelSolve = async (intelId: number) => {
    const answer = intelAnswers[intelId]
    if (!answer) {
      alert('Enter a solution attempt first.')
      return
    }
    try {
      await solveIntel(intelId, answer)
      setIntelAnswers((prev) => ({ ...prev, [intelId]: '' }))
      await loadGameState()
    } catch (err) {
      console.error(err)
      alert('Incorrect solution or puzzle already solved.')
    }
  }

  const handleApplyFalseFlag = async (proposalId: number) => {
    const target = falseFlagTargets[proposalId]
    if (!target) {
      alert('Choose a nation to blame before applying a false flag.')
      return
    }
    try {
      await applyFalseFlag(proposalId, Number(target))
      setFalseFlagTargets((prev) => ({ ...prev, [proposalId]: '' }))
      await loadGameState()
    } catch (err) {
      console.error(err)
      alert('Unable to apply false flag to this proposal.')
    }
  }

  const handleVetoProposal = async (proposalId: number) => {
    try {
      await vetoProposal(proposalId)
      await loadGameState()
      await refreshPreview()
    } catch (err) {
      console.error(err)
      alert('Unable to veto this proposal (limit reached or already locked).')
    }
  }

  const activeProposals: Proposal[] = data.proposals || []

  return (
    <div className="min-h-screen bg-warroom-blue text-slate-100">
      <div className="crt-overlay" />
      {doomActive && <DoomOverlay message={doomMessage} />}
      {escalationFlash && <EscalationAlert flash={escalationFlash} />}
      {crisisFlash && <CrisisAlert crisis={crisisFlash} />}
      <NewsTicker news={newsFeed} />
      <header className="border-b border-slate-700 bg-warroom-slate/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400">Team</p>
            <h1 className="font-pixel text-lg text-warroom-cyan text-glow flex items-center gap-2">{data.team.nation_name}<span className={`inline-block h-2 w-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-500'}`} title={connected ? 'Connected' : 'Disconnected'} /></h1>
            <p className="text-xs text-slate-400">Role: {data.team.role ?? 'player'}</p>
          </div>
          <div className="text-right space-y-2">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400">Round {timer.round}</p>
              <p className={`font-pixel text-xl text-warroom-amber ${timer.state === 'paused' ? 'animate-pulse' : ''}`}>{timerDisplay}</p>
            </div>
            <div className="flex flex-col items-end gap-1">
              <div className="h-2 w-40 overflow-hidden rounded-full bg-slate-800/60">
                <div
                  className={`h-2 rounded-full transition-all duration-300 ${timer.state === 'paused' ? 'bg-warroom-amber/70 animate-pulse' : 'bg-warroom-cyan'}`}
                  style={{ width: `${(timerProgress * 100).toFixed(1)}%` }}
                />
              </div>
              {timer.state === 'paused' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Paused by GM</p>}
              {timer.state === 'complete' && <p className="text-[10px] uppercase tracking-widest text-slate-400">Submissions locked</p>}
              <p className="text-[10px] uppercase tracking-widest text-slate-400">Global Escalation: {totalEscalation}{nextThreshold ? ` → Next at ${nextThreshold}` : ''}</p>
              <DoomsdayClock escalation={totalEscalation} />
            </div>
            <div className="flex gap-2 justify-end">
              <button className="rounded border border-warroom-cyan/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-warroom-cyan hover:border-warroom-cyan" onClick={() => setIsBriefingOpen(true)}>
                View Briefing
              </button>
              <button className="rounded border border-warroom-amber/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-warroom-amber hover:border-warroom-amber" onClick={() => setIsNationsOpen(true)}>
                Nations Intel
              </button>
            </div>
          </div>
        </div>
      </header>
      {isBriefingOpen && <BriefingModal briefing={data.briefing} onClose={() => setIsBriefingOpen(false)} />}
      {isNationsOpen && <NationsModal myTeamId={data.team.id} entries={leaderboard?.entries ?? []} alliances={data.alliances} diplomacyChannels={diplomacyChannels} onClose={() => setIsNationsOpen(false)} />}

      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[4fr_1fr]">
        <section className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow-lg shadow-warroom-cyan/10 space-y-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Action Console</h2>
          {!nukeUnlocked && <p className="text-xs text-warroom-amber">Catastrophic actions are locked until the GM escalates the scenario.</p>}
          {nukeUnlocked && <p className="text-xs text-warroom-amber">☢ Nuclear options are live. Any successful strike ends the game immediately.</p>}
          {activeCrisis && <ActiveCrisisBanner crisis={activeCrisis} />}
          {doomActive && <p className="text-xs text-warroom-amber">Game over state detected — inputs frozen.</p>}
          <div className="grid gap-4 md:grid-cols-3">
            {SLOT_IDS.map((slot) => (
              <div key={slot} className="rounded-lg border border-slate-700/70 bg-warroom-slate/60 p-3">
                <p className="text-xs uppercase tracking-wider text-slate-400">Slot {slot}</p>
                <select className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-sm disabled:opacity-50" value={selection[slot] ?? ''} onChange={(e) => handleSelectionChange(slot, e.target.value)} disabled={doomActive}>
                  <option value="">Select action</option>
                  {availableActions.map((action) => (
                    <option key={action.code} value={action.code} style={{ color: getCategoryColor(action.category) }}>
                      {action.name}
                    </option>
                  ))}
                </select>
                {actions.find((a) => a.code === selection[slot])?.target_required && (
                  <select className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-sm disabled:opacity-50" value={targets[slot] ?? ''} onChange={(e) => handleTargetChange(slot, parseInt(e.target.value))} disabled={doomActive}>
                    <option value="">Select target</option>
                    {teamOptions.map((entry) => (
                      <option key={entry.team_id} value={entry.team_id}>
                        {entry.nation_name}
                      </option>
                    ))}
                  </select>
                )}
                <button
                  className={`mt-3 w-full rounded border border-slate-600 bg-warroom-blue/60 py-2 text-xs font-bold tracking-wide text-warroom-cyan transition hover:border-warroom-cyan ${doomActive ? 'cursor-not-allowed opacity-50 hover:border-slate-600' : ''}`}
                  onClick={() => handleSubmitProposal(slot)}
                  disabled={doomActive}
                >
                  Submit Proposal
                </button>
              </div>
            ))}
          </div>
          <div>
            <h3 className="font-pixel text-xs text-warroom-cyan">Team Proposals</h3>
            <div className="mt-3 space-y-2">
              {activeProposals.length === 0 && <p className="text-xs text-slate-400">No proposals yet.</p>}
              {activeProposals.map((proposal) => {
                const totalVotes = proposal.votes?.reduce((sum, vote) => sum + vote.value, 0) ?? 0
                const locked = proposal.status === 'locked'
                const closed = proposal.status === 'closed'
                const votingDisabled = locked || closed || doomActive
                return (
                  <div key={proposal.id} className="rounded border border-slate-700 bg-warroom-blue/40 px-3 py-2 text-sm text-slate-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold">
                          Slot {proposal.slot}: {actionName(proposal.action_code)}
                        </p>
                        {proposal.target_team_id && <p className="text-xs text-slate-400">Target: {teamOptions.find((t) => t.team_id === proposal.target_team_id)?.nation_name ?? proposal.target_team_id}</p>}
                        {locked && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Locked In</p>}
                        {closed && <p className="text-[10px] uppercase tracking-widest text-slate-400">Closed</p>}
                        {proposal.false_flag_target_team_id && (
                          <p className="text-[10px] uppercase tracking-widest text-warroom-cyan">
                            False flag queued: {teamOptions.find((team) => team.team_id === proposal.false_flag_target_team_id)?.nation_name ?? proposal.false_flag_target_team_id}
                          </p>
                        )}
                        {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Vetoed by Peace Council</p>}
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="rounded border border-slate-600 px-2 text-xs disabled:opacity-40" onClick={() => handleVote(proposal.id, 1)} disabled={votingDisabled}>
                          ▲
                        </button>
                        <span className="text-warroom-amber">{totalVotes}</span>
                        <button className="rounded border border-slate-600 px-2 text-xs disabled:opacity-40" onClick={() => handleVote(proposal.id, -1)} disabled={votingDisabled}>
                          ▼
                        </button>
                      </div>
                    </div>
                    {!proposal.false_flag_target_team_id && proposal.status === 'draft' && falseFlagCount > 0 && (
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        <select
                          className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1"
                          value={falseFlagTargets[proposal.id] ?? ''}
                          onChange={(e) =>
                            setFalseFlagTargets((prev) => ({
                              ...prev,
                              [proposal.id]: e.target.value === '' ? '' : Number(e.target.value),
                            }))
                          }
                        >
                          <option value="">Select blame nation</option>
                          {teamOptions.map((entry) => (
                            <option key={entry.team_id} value={entry.team_id}>
                              {entry.nation_name}
                            </option>
                          ))}
                        </select>
                        <button className="rounded border border-warroom-amber/40 bg-warroom-amber/10 px-3 py-1 text-xs uppercase tracking-widest text-warroom-amber" onClick={() => handleApplyFalseFlag(proposal.id)}>
                          False Flag
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4">
            <h3 className="font-pixel text-xs text-warroom-cyan">Intel Drops</h3>
            <div className="mt-3 space-y-2 text-sm text-slate-300">
              {data.intel_drops.map((intel) => (
                <div key={intel.id} className="rounded border border-slate-700/60 p-3 hack-pulse">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-100">{intel.title}</span>
                    <span className={`text-xs uppercase ${intel.status === 'solved' ? 'text-emerald-400' : 'text-warroom-amber'}`}>{intel.status}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">{intel.description}</p>
                  <p className="mt-2 text-xs text-warroom-cyan">Reward: {intel.reward}</p>
                  {intel.status !== 'solved' && (
                    <div className="mt-2 flex items-center gap-2">
                      <input className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-xs" placeholder="Enter solution..." value={intelAnswers[intel.id] ?? ''} onChange={(e) => setIntelAnswers((prev) => ({ ...prev, [intel.id]: e.target.value }))} />
                      <button className="rounded border border-warroom-cyan/40 bg-warroom-cyan/10 px-3 py-1 text-xs uppercase tracking-widest text-warroom-cyan" onClick={() => handleIntelSolve(intel.id)}>
                        Submit
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4">
            <h3 className="font-pixel text-xs text-warroom-cyan">Lifelines</h3>
            {lifelines.length === 0 && <p className="mt-2 text-xs text-slate-400">No lifelines available.</p>}
            {lifelines.length > 0 && (
              <ul className="mt-2 space-y-1 text-xs text-slate-300">
                {lifelines.map((lifeline) => (
                  <li key={lifeline.id} className="rounded border border-slate-700/50 bg-warroom-blue/30 px-2 py-1">
                    <span className="font-semibold text-slate-100">{lifeline.lifeline_type.replace(/_/g, ' ')}</span>: {lifeline.remaining_uses} remaining
                  </li>
                ))}
              </ul>
            )}
          </div>
          {isUN && previewData && (
            <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4 text-sm text-slate-200">
              <div className="flex items-center justify-between">
                <h3 className="font-pixel text-xs text-warroom-cyan">Peace Council Oversight</h3>
                <p className="text-[10px] uppercase tracking-widest text-slate-400">
                  Vetoes {previewData.vetoes_used}/{previewData.limit}
                </p>
              </div>
              <div className="mt-3 space-y-3 max-h-56 overflow-y-auto">
                {previewData.teams.map((team) => (
                  <div key={team.team_id} className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2">
                    <p className="text-xs uppercase text-slate-400">{team.nation_name}</p>
                    {team.proposals.map((proposal) => (
                      <div key={proposal.id} className="mt-1 rounded border border-slate-700/50 bg-slate-900/40 p-2 text-xs">
                        <p>
                          Slot {proposal.slot}: {proposal.action_code} ({proposal.status}) — votes {proposal.votes}
                        </p>
                        {proposal.status === 'draft' && !vetoLimitReached && (
                          <button className="mt-1 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1 text-[10px] uppercase tracking-widest text-warroom-amber" onClick={() => handleVetoProposal(proposal.id)}>
                            Veto Proposal
                          </button>
                        )}
                        {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Vetoed</p>}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className="space-y-6">
          {leaderboard && (
            <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow shadow-warroom-cyan/10">
              <h3 className="font-pixel text-xs text-warroom-cyan">Outcome Leaderboard</h3>
              <ul className="mt-3 space-y-2 text-sm">
                {leaderboard.entries.slice(0, 5).map((entry, idx) => (
                  <li key={entry.team_id} className="flex items-center justify-between text-slate-300">
                    <span>
                      <span className="mr-2 text-warroom-amber">#{idx + 1}</span>
                      {entry.nation_name}
                    </span>
                    <span className="font-semibold text-warroom-cyan">{entry.score}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow shadow-warroom-cyan/10">
            <h3 className="font-pixel text-xs text-warroom-cyan">Advisors</h3>
            <div className="mt-3 space-y-3">
              {data.advisors.map((advisor) => (
                <div key={advisor.name} className="rounded border border-slate-700/60 p-3">
                  <p className="text-xs text-slate-400">{advisor.name}</p>
                  <p className="text-sm text-slate-100">{advisor.hint}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 flex flex-col gap-3 min-h-[300px]">
            <h3 className="font-pixel text-xs text-warroom-cyan">Team Comms</h3>
            <p className="text-xs text-slate-500">{data.communications_hint}</p>
            <div className="flex-1 overflow-y-auto rounded border border-slate-700/60 bg-warroom-blue/40 p-3 text-sm text-slate-300 min-h-[200px]">
              {messages.map((line, idx) => (
                <p key={idx}>
                  <span className="text-warroom-cyan">{line.display_name}:</span> {line.content}
                </p>
              ))}
              <div ref={chatEndRef} />
            </div>
            <ChatComposer onSend={sendMessage} />
          </div>
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
            <h3 className="font-pixel text-xs text-warroom-cyan">Diplomacy</h3>
            <div className="mt-2 flex items-center gap-2">
              <select className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-xs" value={diplomacyTarget} onChange={(e) => setDiplomacyTarget(Number(e.target.value))}>
                <option value="">Select nation</option>
                {teamOptions.map((entry) => (
                  <option key={entry.team_id} value={entry.team_id}>
                    {entry.nation_name}
                  </option>
                ))}
              </select>
              <button className="rounded border border-slate-600 bg-warroom-cyan/30 px-3 py-1 text-xs" onClick={handleStartDiplomacy}>Open Channel</button>
            </div>
            <div className="mt-3 space-y-3">
              {diplomacyChannels.length === 0 && <p className="text-xs text-slate-500">No diplomacy channels yet.</p>}
              {diplomacyChannels.map((channel: any) => (
                <div key={channel.channel_id} className="rounded border border-slate-700/70 bg-warroom-blue/40 p-2">
                  <p className="text-xs uppercase text-slate-400">With {channel.with_team?.nation_name ?? 'Unknown'}</p>
                  <div className="mt-2 max-h-24 overflow-y-auto space-y-1 text-xs text-slate-300">
                    {channel.messages.map((msg: any) => (
                      <div key={msg.id}>
                        <span className="text-warroom-cyan">{msg.display_name ?? msg.user_id}</span>: {msg.content}
                      </div>
                    ))}
                  </div>
                  <input className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-xs" placeholder="Message..." value={diplomacyDrafts[channel.channel_id] ?? ''} onChange={(e) => setDiplomacyDrafts((prev) => ({ ...prev, [channel.channel_id]: e.target.value }))} />
                  <button className="mt-1 w-full rounded border border-slate-600 bg-warroom-amber/30 py-1 text-xs" onClick={() => handleSendDiplomacy(channel.channel_id)}>Send</button>
                </div>
              ))}
            </div>
            {data.alliances.length > 0 && (
              <div className="mt-3 rounded border border-slate-700/70 bg-warroom-blue/30 p-2">
                <p className="text-xs uppercase text-slate-400">Active Alliances</p>
                <ul className="mt-1 space-y-1 text-xs text-slate-300">
                  {data.alliances.map((alliance) => {
                    const partner =
                      alliance.team_a_id === data.team.id
                        ? leaderboard?.entries.find((entry) => entry.team_id === alliance.team_b_id)?.nation_name
                        : leaderboard?.entries.find((entry) => entry.team_id === alliance.team_a_id)?.nation_name
                    return <li key={`${alliance.team_a_id}-${alliance.team_b_id}`}>{partner ?? 'Unknown partner'}</li>
                  })}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
            <h3 className="font-pixel text-xs text-warroom-cyan">World News</h3>
            <p className="mt-2 text-slate-300">{data.narrative}</p>
          </div>

          {shouldShowReveal && revealData && (
            <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
              <h3 className="font-pixel text-xs text-warroom-cyan">Reveal Preview</h3>
              <div className="mt-2 space-y-2">
                {revealData.ai_models.map((model, index) => (
                  <div key={index} className="rounded border border-slate-700/60 bg-slate-900/40 p-2">
                    <p className="text-slate-200 font-semibold">{model.model_name}</p>
                    <p className="text-xs text-slate-400">Avg escalation: {Math.round(model.avg_escalation)}</p>
                    <p className="text-xs text-slate-400">First violent round: {model.first_violent_round}</p>
                    <p className="text-xs text-warroom-amber">{model.launched_nukes ? 'Launched nukes' : 'Did not launch nukes'}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-400">
                Human outcome {revealData.human_vs_ai.human_outcome} vs AI outcome {revealData.human_vs_ai.ai_outcome}
              </p>
            </div>
          )}

          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
            <h3 className="font-pixel text-xs text-warroom-cyan">Round History</h3>
            <div className="mt-2 max-h-48 overflow-y-auto space-y-1 text-xs text-slate-400">
              {historyEntries.length === 0 && <p>No actions resolved yet.</p>}
              {historyEntries.map((entry) => (
                <div key={entry.id} className="rounded border border-slate-700/50 bg-slate-800/40 p-2">
                  <p className="text-slate-200">
                    Round {entry.round} — {entry.actor ?? 'Unknown'} used {entry.action_code}
                    {entry.target ? ` on ${entry.target}` : ''} ({entry.success ? 'SUCCESS' : 'FAILED'})
                  </p>
                  <p className="text-[10px] uppercase tracking-widest text-slate-500">Slot {entry.slot}</p>
                </div>
              ))}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}

function SpectatorView({ leaderboard, timer, reveal, news, global }: { leaderboard: LeaderboardResponse | null; timer: RoundTimer; reveal: RevealData | null; news: Array<{ id: number; message: string }>; global?: GlobalStatePayload | null }) {
  if (!leaderboard) {
    return <div className="flex min-h-screen items-center justify-center bg-warroom-blue text-slate-100">Waiting for game state…</div>
  }
  const timerText = formatTimerDisplay(timer)
  const progress = timer.duration ? Math.max(0, Math.min(1, timer.remaining / timer.duration)) : 0
  const crisis = global?.active_crisis ?? null
  const doomActive = global?.doom_triggered ?? false
  const totalEscalation = global?.total_escalation ?? 0
  return (
    <div className="min-h-screen bg-warroom-blue text-slate-100">
      <NewsTicker news={news} />
      <div className="mx-auto max-w-5xl px-6 py-8">
        <h1 className="font-pixel text-2xl text-warroom-cyan">Cyber War Room — Live Leaderboard</h1>
        <div className="space-y-2">
          <p className="text-sm text-slate-400">Round {timer.round} • {timerText}</p>
          <div className="h-2 w-48 overflow-hidden rounded-full bg-slate-800/60">
            <div
              className={`h-2 rounded-full ${timer.state === 'paused' ? 'bg-warroom-amber/70 animate-pulse' : 'bg-warroom-cyan/70'}`}
              style={{ width: `${(progress * 100).toFixed(1)}%` }}
            />
          </div>
          {timer.state === 'paused' && <p className="text-xs text-warroom-amber">GM has paused submissions</p>}
          {timer.state === 'complete' && <p className="text-xs text-slate-400">Timer elapsed — awaiting resolution</p>}
          {doomActive && <p className="text-xs text-warroom-amber">Catastrophic strike detected — game over.</p>}
          <div className="flex items-center gap-3">
            <p className="text-xs text-slate-400">Global Escalation: {totalEscalation}</p>
            <DoomsdayClock escalation={totalEscalation} />
          </div>
        </div>
        {crisis && (
          <div className="mt-4 rounded border border-warroom-amber/60 bg-warroom-amber/10 p-4 text-sm text-warroom-amber">
            <p className="font-pixel text-xs uppercase tracking-widest">Active Crisis</p>
            <p className="text-base">{crisis.title}</p>
            <p className="text-warroom-amber/80">{crisis.summary}</p>
            <p className="text-xs text-warroom-amber/70">{crisis.effect}</p>
          </div>
        )}
        <div className="mt-4 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h3 className="font-pixel text-xs text-warroom-cyan">Escalation Trend</h3>
          <EscalationChart series={leaderboard.escalation_series} />
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {leaderboard.entries.map((entry) => (
            <div key={entry.team_id} className="rounded border border-slate-700 bg-slate-900/60 p-4">
              <p className="text-lg font-semibold text-warroom-amber">{entry.nation_name}</p>
              <p className="text-sm text-slate-400">Outcome Score: {entry.score} (Δ {entry.delta_from_baseline})</p>
              <p className="text-xs text-slate-500">Escalation: {entry.escalation}</p>
            </div>
          ))}
        </div>
        <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h3 className="font-pixel text-xs text-warroom-cyan">Score Overview</h3>
          <LeaderboardBarChart entries={leaderboard.entries.map(e => ({ nation_name: e.nation_name, score: e.score, baseline: e.score - (e.delta_from_baseline ?? 0) }))} />
        </div>
        {reveal && doomActive && (
          <div className="mt-8 rounded border border-slate-700 bg-slate-900/60 p-4">
            <h2 className="font-pixel text-sm text-warroom-cyan">AI Shadow Comparison</h2>
            <div className="mt-2 grid gap-3 md:grid-cols-3">
              {reveal.ai_models.map((model, index) => (
                <div key={index} className="rounded border border-slate-700/60 bg-slate-900/40 p-3 text-xs text-slate-300">
                  <p className="text-slate-100 font-semibold">{model.model_name}</p>
                  <p>Avg escalation: {Math.round(model.avg_escalation)}</p>
                  <p>First violent round: {model.first_violent_round}</p>
                  <p>{model.launched_nukes ? 'Launched nuclear strike' : 'No nukes'}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-slate-300">Human outcome: {reveal.human_vs_ai.human_outcome} vs AI outcome: {reveal.human_vs_ai.ai_outcome}</p>
          </div>
        )}
      </div>
    </div>
  )
}

function AdminPanel() {
  const [message, setMessage] = useState<string | null>(null)
  const [rounds, setRounds] = useState<any[]>([])
  const [globalStatus, setGlobalStatus] = useState<GlobalStatePayload | null>(null)
  const [crisisHistory, setCrisisHistory] = useState<CrisisInfo[]>([])
  const [availableCrises, setAvailableCrises] = useState<CrisisInfo[]>([])
  const [selectedCrisis, setSelectedCrisis] = useState('')
  const [proposalPreview, setProposalPreview] = useState<any | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const data = await adminFetchStatus()
      setGlobalStatus(data.global ?? DEFAULT_GLOBAL_STATE)
      setCrisisHistory(data.crises ?? [])
      setAvailableCrises(data.available_crises ?? [])
      setProposalPreview(data.proposal_preview ?? null)
    } catch (err) {
      console.error(err)
      setMessage('Failed to fetch GM status — ensure you are authenticated.')
    }
  }, [])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  const call = async (action: 'start' | 'advance' | 'reset' | 'list' | 'pause' | 'resume') => {
    try {
      setMessage('Working…')
      if (action === 'start') {
        await adminStartRound()
        setMessage('Round started')
      } else if (action === 'advance') {
        await adminAdvanceRound()
        setMessage('Round resolved and advanced')
      } else if (action === 'reset') {
        await adminResetRounds()
        setMessage('Rounds reset')
      } else if (action === 'pause') {
        await adminPauseTimer()
        setMessage('Timer paused')
      } else if (action === 'resume') {
        await adminResumeTimer()
        setMessage('Timer resumed')
      } else {
        const data = await adminListRounds()
        setRounds(data)
        setMessage('Fetched round status')
      }
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Admin action failed — ensure you are logged in as GM.')
    }
  }

  const gmVetoProposal = async (proposalId: number) => {
    try {
      await vetoProposal(proposalId)
      setMessage('Veto issued')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Veto failed — proposal may already be locked.')
    }
  }

  const toggleNukes = async () => {
    try {
      const unlocked = !(globalStatus?.nuke_unlocked ?? false)
      await adminToggleNukes(unlocked)
      setMessage(unlocked ? 'Nuclear actions unlocked' : 'Nuclear actions locked')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Failed to toggle nuclear state.')
    }
  }

  const injectCrisis = async () => {
    if (!selectedCrisis) {
      setMessage('Select a crisis before injecting.')
      return
    }
    try {
      await adminInjectCrisis(selectedCrisis)
      setMessage(`Crisis ${selectedCrisis} injected.`)
      setSelectedCrisis('')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Failed to inject crisis.')
    }
  }

  const clearCrisis = async () => {
    try {
      await adminClearCrisis()
      setMessage('Active crisis cleared.')
      refreshStatus()
    } catch (err) {
      console.error(err)
      setMessage('Failed to clear crisis.')
    }
  }

  return (
    <div className="min-h-screen bg-warroom-blue px-6 py-8 text-slate-100">
      <h1 className="font-pixel text-xl text-warroom-cyan">GM Control Panel</h1>
      <div className="mt-4 flex flex-wrap gap-3">
        <button className="rounded border border-slate-600 bg-warroom-amber/40 px-4 py-2 text-sm" onClick={() => call('start')}>Start Round</button>
        <button className="rounded border border-slate-600 bg-warroom-cyan/30 px-4 py-2 text-sm" onClick={() => call('advance')}>Resolve & Advance</button>
        <button className="rounded border border-slate-600 bg-slate-700 px-4 py-2 text-sm" onClick={() => call('reset')}>Reset Rounds</button>
        <button className="rounded border border-slate-600 bg-slate-700 px-4 py-2 text-sm" onClick={() => call('list')}>List Rounds</button>
        <button className="rounded border border-slate-600 bg-warroom-amber/30 px-4 py-2 text-sm" onClick={() => call('pause')}>Pause Timer</button>
        <button className="rounded border border-slate-600 bg-warroom-cyan/30 px-4 py-2 text-sm" onClick={() => call('resume')}>Resume Timer</button>
      </div>
      {message && <p className="mt-4 text-sm text-slate-300">{message}</p>}
      {rounds.length > 0 && (
        <div className="mt-6 space-y-2">
          {rounds.map((round: any) => (
            <div key={round.id} className="rounded border border-slate-700 bg-slate-900/60 p-3 text-sm">
              Round {round.round_number}: {round.status} (start: {round.started_at ?? '—'})
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Nuclear Controls</h2>
          <p className="mt-2 text-sm text-slate-300">Current state: {globalStatus?.nuke_unlocked ? 'Unlocked' : 'Locked'}</p>
          <button className="mt-3 w-full rounded border border-warroom-amber/50 bg-warroom-amber/20 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-amber" onClick={toggleNukes}>
            {globalStatus?.nuke_unlocked ? 'Lock Nuclear Options' : 'Unlock Nuclear Options'}
          </button>
          {globalStatus?.doom_triggered && <p className="mt-3 text-xs text-warroom-amber">Game-over state active: {globalStatus.doom_message}</p>}
        </div>
        <div className="rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Crisis Injection</h2>
          <select className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-sm" value={selectedCrisis} onChange={(e) => setSelectedCrisis(e.target.value)}>
            <option value="">Select crisis</option>
            {availableCrises.map((crisis) => (
              <option key={crisis.code} value={crisis.code}>
                {crisis.title}
              </option>
            ))}
          </select>
          <div className="mt-3 flex gap-2">
            <button className="flex-1 rounded border border-warroom-cyan/50 bg-warroom-cyan/20 px-3 py-2 text-xs font-semibold uppercase tracking-widest text-warroom-cyan" onClick={injectCrisis}>
              Inject Crisis
            </button>
            <button className="flex-1 rounded border border-slate-600 bg-slate-800 px-3 py-2 text-xs uppercase tracking-widest text-slate-300" onClick={clearCrisis}>
              Clear Crisis
            </button>
          </div>
          {globalStatus?.active_crisis && (
            <div className="mt-3 rounded border border-warroom-amber/50 bg-warroom-amber/10 p-3 text-xs text-warroom-amber">
              <p className="font-semibold uppercase tracking-widest">Active Crisis</p>
              <p className="text-sm">{globalStatus.active_crisis.title}</p>
              <p>{globalStatus.active_crisis.summary}</p>
            </div>
          )}
        </div>
      </div>

      {crisisHistory.length > 0 && (
        <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Crisis Log</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            {crisisHistory.map((item) => (
              <li key={`${item.code}-${item.applied_at}`} className="rounded border border-slate-700/60 p-3">
                <p className="text-warroom-amber">{item.title}</p>
                <p className="text-xs text-slate-400">{item.applied_at}</p>
                <p className="text-xs">{item.summary}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {proposalPreview && (
        <div className="mt-6 rounded border border-slate-700 bg-slate-900/60 p-4">
          <h2 className="font-pixel text-sm text-warroom-cyan">Proposal Oversight</h2>
          <p className="text-xs text-slate-400">Vetoes used: {proposalPreview.vetoes_used}/{proposalPreview.limit}</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {proposalPreview.teams.map((team: ProposalPreview) => (
              <div key={team.team_id} className="rounded border border-slate-700/60 bg-warroom-blue/20 p-3 text-xs text-slate-300">
                <p className="text-xs uppercase text-slate-400">{team.nation_name}</p>
                <div className="mt-2 space-y-2">
                  {team.proposals.map((proposal) => (
                    <div key={proposal.id} className="rounded border border-slate-700/60 bg-slate-900/40 p-2">
                      <p>
                        Slot {proposal.slot}: {proposal.action_code} ({proposal.status}) — votes {proposal.votes}
                      </p>
                      {proposal.status === 'draft' && (
                        <button className="mt-1 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1 text-[10px] uppercase tracking-widest text-warroom-amber" onClick={() => gmVetoProposal(proposal.id)}>
                          Veto
                        </button>
                      )}
                      {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Already vetoed</p>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function BriefingModal({ briefing, onClose }: { briefing: GameState['briefing']; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-lg border border-warroom-cyan/40 bg-slate-900/90 p-6 shadow-2xl shadow-warroom-cyan/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-warroom-cyan">{briefing.title}</h2>
          <button className="text-xs uppercase text-slate-400 hover:text-warroom-cyan" onClick={onClose}>
            Close
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-200">{briefing.summary}</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded border border-slate-700 p-3">
            <p className="font-semibold text-warroom-amber">Allies</p>
            <ul className="mt-2 list-disc pl-4 text-sm text-slate-300">
              {briefing.allies.map((ally, idx) => (
                <li key={idx}>{ally}</li>
              ))}
            </ul>
          </div>
          <div className="rounded border border-slate-700 p-3">
            <p className="font-semibold text-warroom-amber">Threats</p>
            <ul className="mt-2 list-disc pl-4 text-sm text-slate-300">
              {briefing.threats.map((threat, idx) => (
                <li key={idx}>{threat}</li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-4 rounded border border-slate-700 p-3">
          <p className="font-semibold text-warroom-amber">Consequences</p>
          <p className="mt-2 text-sm text-slate-300">{briefing.consequences}</p>
        </div>
      </div>
    </div>
  )
}

function NationsModal({ myTeamId, entries, alliances, diplomacyChannels, onClose }: {
  myTeamId: number
  entries: Array<{ team_id: number; nation_name: string; score: number; delta_from_baseline: number; escalation: number }>
  alliances: Array<{ team_a_id: number; team_b_id: number; status: string; formed_at: string | null }>
  diplomacyChannels: any[]
  onClose: () => void
}) {
  const alliedIds = new Set(
    alliances.map((a) => (a.team_a_id === myTeamId ? a.team_b_id : a.team_a_id))
  )
  const diplomacyIds = new Set(
    diplomacyChannels.map((ch: any) => ch.with_team?.id ?? ch.target_team_id).filter(Boolean)
  )

  const getRelationship = (teamId: number) => {
    if (teamId === myTeamId) return 'you'
    if (alliedIds.has(teamId)) return 'allied'
    if (diplomacyIds.has(teamId)) return 'diplomatic'
    return 'neutral'
  }

  const relationshipLabel = (rel: string) => {
    switch (rel) {
      case 'you': return { text: 'YOU', color: 'text-warroom-cyan' }
      case 'allied': return { text: 'ALLIED', color: 'text-emerald-400' }
      case 'diplomatic': return { text: 'IN CONTACT', color: 'text-warroom-amber' }
      default: return { text: 'NEUTRAL', color: 'text-slate-500' }
    }
  }

  const sorted = [...entries].sort((a, b) => b.score - a.score)
  const myEntry = entries.find((e) => e.team_id === myTeamId)
  const myRank = sorted.findIndex((e) => e.team_id === myTeamId) + 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg border border-warroom-amber/40 bg-slate-900/95 p-6 shadow-2xl shadow-warroom-amber/20">
        <div className="flex items-center justify-between">
          <h2 className="font-pixel text-warroom-amber">Nations Intel</h2>
          <button className="text-xs uppercase text-slate-400 hover:text-warroom-amber" onClick={onClose}>Close</button>
        </div>
        {myEntry && (
          <div className="mt-3 rounded border border-warroom-cyan/40 bg-warroom-cyan/5 p-3 text-sm">
            <p className="text-xs uppercase tracking-widest text-slate-400">Your Standing</p>
            <p className="text-warroom-cyan font-semibold">{myEntry.nation_name} — Rank #{myRank} of {entries.length}</p>
            <p className="text-xs text-slate-400">Score: {myEntry.score} (delta {myEntry.delta_from_baseline >= 0 ? '+' : ''}{myEntry.delta_from_baseline}) | Escalation: {myEntry.escalation}</p>
          </div>
        )}
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {sorted.map((entry, idx) => {
            const rel = getRelationship(entry.team_id)
            const label = relationshipLabel(rel)
            const isMe = entry.team_id === myTeamId
            return (
              <div key={entry.team_id} className={`rounded border p-3 ${isMe ? 'border-warroom-cyan/50 bg-warroom-cyan/5' : 'border-slate-700/70 bg-warroom-blue/30'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-warroom-amber font-pixel text-xs">#{idx + 1}</span>
                    <span className={`font-semibold ${isMe ? 'text-warroom-cyan' : 'text-slate-100'}`}>{entry.nation_name}</span>
                  </div>
                  <span className={`text-[10px] uppercase tracking-widest font-semibold ${label.color}`}>{label.text}</span>
                </div>
                <div className="mt-2 flex gap-4 text-xs text-slate-400">
                  <span>Score: <span className="text-slate-200">{entry.score}</span></span>
                  <span>Delta: <span className={entry.delta_from_baseline >= 0 ? 'text-emerald-400' : 'text-red-400'}>{entry.delta_from_baseline >= 0 ? '+' : ''}{entry.delta_from_baseline}</span></span>
                  <span>Escalation: <span className={entry.escalation > 20 ? 'text-red-400' : entry.escalation > 10 ? 'text-warroom-amber' : 'text-slate-200'}>{entry.escalation}</span></span>
                </div>
                {rel === 'allied' && <p className="mt-1 text-[10px] uppercase tracking-widest text-emerald-400/70">Active alliance in place</p>}
                {rel === 'diplomatic' && <p className="mt-1 text-[10px] uppercase tracking-widest text-warroom-amber/70">Diplomacy channel open</p>}
              </div>
            )
          })}
        </div>
        <div className="mt-4 flex gap-4 text-[10px] uppercase tracking-widest text-slate-500">
          <span><span className="text-emerald-400">///</span> Allied</span>
          <span><span className="text-warroom-amber">///</span> In Contact</span>
          <span><span className="text-slate-500">///</span> Neutral</span>
        </div>
      </div>
    </div>
  )
}

function ActiveCrisisBanner({ crisis }: { crisis: CrisisInfo }) {
  return (
    <div className="rounded border border-warroom-amber/60 bg-warroom-amber/10 p-4 text-sm text-warroom-amber">
      <p className="font-pixel text-xs uppercase tracking-widest">Active Crisis</p>
      <p className="text-base">{crisis.title}</p>
      <p className="text-warroom-amber/80">{crisis.summary}</p>
      <p className="text-xs text-warroom-amber/70">{crisis.effect}</p>
    </div>
  )
}

function CrisisAlert({ crisis }: { crisis: CrisisInfo }) {
  return (
    <div className="pointer-events-none fixed inset-0 z-30 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-lg rounded border border-warroom-amber/70 bg-warroom-amber/90 p-6 text-center text-slate-900 shadow-2xl shadow-warroom-amber/50">
        <p className="font-pixel text-xs uppercase tracking-[0.4em] text-slate-900">Crisis Alert</p>
        <p className="mt-3 text-2xl font-bold">{crisis.title}</p>
        <p className="mt-2 text-base">{crisis.summary}</p>
        <p className="mt-4 text-sm uppercase tracking-widest text-slate-800">{crisis.effect}</p>
      </div>
    </div>
  )
}

function DoomOverlay({ message }: { message?: string | null }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/80 px-6 text-center">
      <div className="max-w-2xl space-y-4">
        <p className="font-pixel text-3xl text-warroom-amber">☢ GAME OVER — ESCALATION CASCADE</p>
        <p className="text-lg text-slate-100">{message ?? 'A catastrophic strike succeeded. Scenario terminated. Everyone loses.'}</p>
      </div>
    </div>
  )
}

function EscalationAlert({ flash }: { flash: { threshold: number; severity: string; total: number } }) {
  const color =
    flash.severity === 'doom'
      ? 'bg-red-900/80 border-red-400 text-red-100'
      : flash.severity === 'critical'
        ? 'bg-orange-900/80 border-orange-400 text-orange-100'
        : flash.severity === 'warning'
          ? 'bg-warroom-amber/80 border-warroom-amber text-slate-900'
          : 'bg-warroom-cyan/80 border-warroom-cyan text-slate-900'
  return (
    <div className={`fixed top-2 left-1/2 z-40 w-80 -translate-x-1/2 rounded border px-3 py-2 text-center text-xs font-semibold uppercase tracking-widest screen-shake ${color}`}>
      Global escalation {flash.total} crossed {flash.threshold}
    </div>
  )
}

function WrappedApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}

export default WrappedApp

function NewsTicker({ news }: { news: Array<{ id: number; message: string }> }) {
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

function DoomsdayClock({ escalation, maxEscalation = 200 }: { escalation: number; maxEscalation?: number }) {
  const pct = Math.min(100, (escalation / maxEscalation) * 100);
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
  );
}

function EscalationChart({ series }: { series: Array<{ round: number; score: number }> }) {
  if (!series || series.length === 0) {
    return <p className="text-xs text-slate-500">Waiting for data...</p>
  }
  const chartData = series.map((point) => ({ round: `R${point.round}`, escalation: point.score }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="round" stroke="#94a3b8" fontSize={10} />
        <YAxis stroke="#94a3b8" fontSize={10} />
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
        <Line type="monotone" dataKey="escalation" stroke="#ef4444" strokeWidth={2} dot={{ fill: '#ef4444' }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function LeaderboardBarChart({ entries }: { entries: Array<{ nation_name: string; score: number; baseline: number }> }) {
  const data = entries.map(e => ({
    name: e.nation_name.length > 8 ? e.nation_name.slice(0, 8) + '\u2026' : e.nation_name,
    score: e.score,
    delta: e.score - e.baseline,
  }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey="name" stroke="#94a3b8" fontSize={9} angle={-30} textAnchor="end" height={60} />
        <YAxis stroke="#94a3b8" fontSize={10} />
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', color: '#f8fafc' }} />
        <Bar dataKey="score" fill="#38bdf8" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.delta >= 0 ? '#22c55e' : '#ef4444'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

function formatTimerDisplay(timer: RoundTimer): string {
  if (timer.state === 'paused') {
    return 'PAUSED'
  }
  const mins = Math.floor(timer.remaining / 60)
  const secs = timer.remaining % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

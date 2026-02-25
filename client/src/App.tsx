import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import './App.css'
import {
  fetchGameState,
  fetchSession,
  fetchLeaderboard,
  fetchRevealData,
  fetchActions,
  submitProposal,
  castVote,
  ApiError,
  type LeaderboardResponse,
  type RevealData,
  type ActionDefinition,
  type CrisisInfo,
  fetchDiplomacyChannels,
  startDiplomacy,
  sendDiplomacyMessage,
  fetchNews,
  solveIntel,
  applyFalseFlag,
  fetchHistory,
  fetchProposalPreview,
  vetoProposal,
  fetchMegaChallenge,
  solveMegaChallenge,
  usePhoneAFriend,
  type HistoryEntry,
  type ProposalPreview,
  type MegaChallengeData,
} from './lib/api'
import { useChat } from './hooks/useChat'
import { useRoundTimer, type RoundTimer } from './hooks/useRoundTimer'
import { getTeamSocket, getGlobalSocket } from './lib/socket'
import {
  SLOT_IDS,
  DEFAULT_GLOBAL_STATE,
  getCategoryColor,
  formatTimerDisplay,
  type Proposal,
  type GameState,
  type GlobalStatePayload,
} from './lib/gameUtils'

import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthPanel } from './components/AuthPanel'
import { ChatComposer } from './components/ChatComposer'
import { SpectatorView } from './components/SpectatorView'
import { AdminPanel } from './components/AdminPanel'
import { BriefingModal, NationsModal, HowToPlayModal } from './components/modals'
import { DoomOverlay, CrisisAlert, EscalationAlert, ActiveCrisisBanner } from './components/overlays'
import { NewsTicker } from './components/NewsTicker'
import { DoomsdayClock } from './components/DoomsdayClock'

const viewMode = new URLSearchParams(window.location.search).get('view') ?? 'player'

function App() {
  const [data, setData] = useState<GameState | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [globalState, setGlobalState] = useState<GlobalStatePayload | null>(null)
  const chatEnabled = !authRequired && Boolean(data?.team?.id)
  const { messages, sendMessage, typingUsers, sendTyping } = useChat(chatEnabled)
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null)
  const [revealData, setRevealData] = useState<RevealData | null>(null)
  const [actions, setActions] = useState<ActionDefinition[]>([])
  const [selection, setSelection] = useState<Record<number, string>>({})
  const [targets, setTargets] = useState<Record<number, number>>({})
  const [timerSeed, setTimerSeed] = useState<RoundTimer>({ round: 1, remaining: 0, duration: 360, state: 'idle' })
  const [isBriefingOpen, setIsBriefingOpen] = useState(false)
  const [isNationsOpen, setIsNationsOpen] = useState(false)
  const [isHelpOpen, setIsHelpOpen] = useState(false)
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
  const [megaChallenge, setMegaChallenge] = useState<MegaChallengeData | null>(null)
  const [megaAnswer, setMegaAnswer] = useState('')
  const [phoneHint, setPhoneHint] = useState<{ team_name: string; action_name: string; slot: number } | null>(null)
  const [toasts, setToasts] = useState<Array<{ id: number; message: string; type: 'info' | 'warning' | 'error' }>>([])
  const toastIdRef = useRef(0)
  const [chatCollapsed, setChatCollapsed] = useState(false)
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
      if (ctx.state === 'suspended') ctx.resume()
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
    if (!isUN) { setPreviewData(null); return }
    try {
      const preview = await fetchProposalPreview()
      setPreviewData(preview)
    } catch (err) { console.error(err) }
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

  // Bootstrap: check session
  useEffect(() => {
    if (viewMode !== 'player') { setStatus('ready'); return }
    let cancelled = false
    const bootstrap = async () => {
      try {
        const session = await fetchSession()
        if (cancelled) return
        if (session.authenticated) { setAuthRequired(false); loadGameState() }
        else { setAuthRequired(true); setStatus('ready') }
      } catch {
        if (cancelled) return
        setAuthRequired(true); setStatus('ready')
      }
    }
    bootstrap()
    return () => { cancelled = true }
  }, [loadGameState])

  // Load actions + mega challenge
  useEffect(() => {
    if (viewMode !== 'player' || authRequired || !data) return
    let cancelled = false
    ;(async () => {
      try { const list = await fetchActions(); if (!cancelled) setActions(list) }
      catch (err) { if (err instanceof ApiError && err.status === 401) { setAuthRequired(true); return }; console.error(err) }
    })()
    ;(async () => {
      try { const mc = await fetchMegaChallenge(); if (!cancelled) setMegaChallenge(mc) }
      catch { /* ignore */ }
    })()
    return () => { cancelled = true }
  }, [authRequired, data])

  // Leaderboard polling
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const lb = await fetchLeaderboard()
        if (!cancelled) {
          setLeaderboard(lb)
          if (lb.timer) setTimerSeed(lb.timer)
          if (lb.global) setGlobalState((prev) => ({ ...(prev ?? DEFAULT_GLOBAL_STATE), ...lb.global }))
        }
      } catch (err) { console.error(err) }
    }
    load()
    const interval = setInterval(load, 10000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  // Reveal trigger
  useEffect(() => {
    if (viewMode === 'gm' || effectiveGlobal.doom_triggered) setShouldShowReveal(true)
  }, [effectiveGlobal.doom_triggered])

  useEffect(() => {
    if (!shouldShowReveal) return
    let cancelled = false
    ;(async () => {
      try { const d = await fetchRevealData(); if (!cancelled) setRevealData(d) }
      catch (err) { if (err instanceof ApiError && err.status === 403) return; console.error(err) }
    })()
    return () => { cancelled = true }
  }, [shouldShowReveal])

  // Diplomacy
  useEffect(() => {
    if (viewMode !== 'player' || authRequired || !data?.team?.id) { setDiplomacyChannels([]); return }
    let cancelled = false
    ;(async () => {
      try { const channels = await fetchDiplomacyChannels(); if (!cancelled) setDiplomacyChannels(channels) }
      catch (err) { if (err instanceof ApiError && err.status === 401) { setAuthRequired(true); return }; console.error(err) }
    })()
    const socket = getTeamSocket()
    const handler = (payload: any) => {
      setDiplomacyChannels((prev) => {
        const copy = prev.map((channel) =>
          channel.channel_id === payload.channel_id
            ? { ...channel, messages: [...channel.messages, { id: payload.id ?? Date.now(), content: payload.content, user_id: payload.team_id, sent_at: payload.sent_at, display_name: payload.display_name }] }
            : channel,
        )
        return copy.length ? copy : prev
      })
    }
    socket.on('diplomacy:message', handler)
    return () => { cancelled = true; socket.off('diplomacy:message', handler) }
  }, [authRequired, data?.team?.id])

  // UN preview polling
  useEffect(() => {
    if (!isUN) { setPreviewData(null); return }
    let cancelled = false
    const load = async () => {
      try { const preview = await fetchProposalPreview(); if (!cancelled) setPreviewData(preview) }
      catch (err) { console.error(err) }
    }
    load()
    const interval = setInterval(load, 7000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [isUN])

  // History polling
  useEffect(() => {
    let cancelled = false
    const loadHistory = async () => {
      try { const response = await fetchHistory(25); if (!cancelled) setHistoryEntries(response.entries) }
      catch (err) { console.error(err) }
    }
    const canFetch = viewMode === 'spectator' || (viewMode === 'player' && !authRequired)
    if (canFetch) {
      loadHistory()
      const interval = setInterval(loadHistory, 10000)
      return () => { cancelled = true; clearInterval(interval) }
    }
    return () => { cancelled = true }
  }, [authRequired])

  // News
  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try { const news = await fetchNews(); if (!cancelled) setNewsFeed(news) }
      catch (err) { console.error(err) }
    })()
    return () => { cancelled = true }
  }, [])

  // Global socket events
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
    const resetHandler = () => {
      loadGameState()
    }
    socket.on('game:nuke_state', nukeHandler)
    socket.on('game:over', doomHandler)
    socket.on('crisis:injected', crisisHandler)
    socket.on('crisis:cleared', crisisClearedHandler)
    socket.on('news:event', newsHandler)
    socket.on('escalation:threshold', escalationHandler)
    socket.on('game:reset', resetHandler)
    return () => {
      socket.off('game:nuke_state', nukeHandler)
      socket.off('game:over', doomHandler)
      socket.off('crisis:injected', crisisHandler)
      socket.off('crisis:cleared', crisisClearedHandler)
      socket.off('news:event', newsHandler)
      socket.off('escalation:threshold', escalationHandler)
      socket.off('game:reset', resetHandler)
    }
  }, [authRequired, playCue, loadGameState])

  // Team socket events
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
                  ? { ...proposal, status: payload.status, vetoed_by_user_id: payload.vetoed_by_user_id ?? null, vetoed_reason: payload.vetoed_reason ?? null }
                  : proposal,
              ),
            }
          : prev,
      )
      if (isUN) refreshPreview()
    }
    socket.on('proposals:auto_locked', autoLockHandler)
    socket.on('proposal:vetoed', vetoHandler)
    return () => {
      socket.off('proposals:auto_locked', autoLockHandler)
      socket.off('proposal:vetoed', vetoHandler)
    }
  }, [authRequired, data?.team?.id, isUN, refreshPreview])

  // Flash timers
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

  const addToast = useCallback((message: string, type: 'info' | 'warning' | 'error' = 'info') => {
    const id = ++toastIdRef.current
    setToasts((prev) => [...prev.slice(-4), { id, message, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000)
  }, [])

  // Connection status
  useEffect(() => {
    const socket = getGlobalSocket()
    setConnected(socket.connected)
    const onConnect = () => setConnected(true)
    const onDisconnect = () => setConnected(false)
    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    return () => { socket.off('connect', onConnect); socket.off('disconnect', onDisconnect) }
  }, [])

  // Session kick
  useEffect(() => {
    const socket = getTeamSocket()
    const onKick = (d: { reason: string }) => { addToast(d.reason || 'Session terminated.', 'error'); setAuthRequired(true) }
    socket.on('session:kick', onKick)
    return () => { socket.off('session:kick', onKick) }
  }, [addToast])

  // Auto-scroll chat
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const timerDisplay = useMemo(() => formatTimerDisplay(timer), [timer])
  const timerProgress = useMemo(() => {
    if (!timer.duration) return 0
    return Math.max(0, Math.min(1, timer.remaining / timer.duration))
  }, [timer.remaining, timer.duration])

  const nukeUnlocked = effectiveGlobal.nuke_unlocked
  const availableActions = useMemo(
    () => actions.filter((action) => nukeUnlocked || action.category !== 'nuclear'),
    [actions, nukeUnlocked],
  )

  // ── View routing ──────────────────────────────────────────────────────

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
    if (authRequired) return <AuthPanel onAuthenticated={handleAuthenticated} errorMessage={error} />
    return (
      <div className="flex min-h-screen items-center justify-center bg-warroom-blue text-center text-slate-100">
        <div>
          <p className="font-pixel text-warroom-amber">CONNECTION LOST</p>
          <p className="mt-2 max-w-sm text-sm text-slate-300">{error}</p>
        </div>
      </div>
    )
  }

  // ── Derived values ────────────────────────────────────────────────────

  const teamOptions = leaderboard?.entries.filter((entry) => entry.team_id !== data.team.id) ?? []
  const lifelines = data.lifelines ?? []
  const falseFlagCount = lifelines.find((item) => item.lifeline_type === 'false_flag')?.remaining_uses ?? 0
  const totalEscalation = effectiveGlobal.total_escalation ?? 0
  const nextThreshold = (effectiveGlobal.escalation_thresholds ?? []).find((value) => value > totalEscalation) ?? null
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
    if (action?.target_required && !targetId) { alert('This action requires selecting a target nation.'); return }
    try {
      await submitProposal(slot, actionCode, targetId)
      setSelection((prev) => ({ ...prev, [slot]: '' }))
      await loadGameState()
    } catch (err) { console.error(err); alert('Failed to submit action.') }
  }

  const handleVote = async (proposalId: number, value: 1 | -1) => {
    if (doomActive) return
    try { await castVote(proposalId, value); await loadGameState() }
    catch (err) { console.error(err); alert('Failed to register vote.') }
  }

  const handleStartDiplomacy = async () => {
    if (!diplomacyTarget) return
    try {
      await startDiplomacy(Number(diplomacyTarget))
      setDiplomacyTarget('')
      const channels = await fetchDiplomacyChannels()
      setDiplomacyChannels(channels)
    } catch (err) { console.error(err); alert('Failed to start diplomacy channel.') }
  }

  const handleSendDiplomacy = async (channelId: number) => {
    const content = diplomacyDrafts[channelId]
    if (!content) return
    try {
      await sendDiplomacyMessage(channelId, content)
      setDiplomacyDrafts((prev) => ({ ...prev, [channelId]: '' }))
    } catch (err) { console.error(err); alert('Failed to send diplomacy message.') }
  }

  const handleIntelSolve = async (intelId: number) => {
    const answer = intelAnswers[intelId]
    if (!answer) { alert('Enter a solution attempt first.'); return }
    try {
      await solveIntel(intelId, answer)
      setIntelAnswers((prev) => ({ ...prev, [intelId]: '' }))
      await loadGameState()
    } catch (err) { console.error(err); alert('Incorrect solution or puzzle already solved.') }
  }

  const handleApplyFalseFlag = async (proposalId: number) => {
    const target = falseFlagTargets[proposalId]
    if (!target) { alert('Choose a nation to blame before applying a false flag.'); return }
    try {
      await applyFalseFlag(proposalId, Number(target))
      setFalseFlagTargets((prev) => ({ ...prev, [proposalId]: '' }))
      await loadGameState()
    } catch (err) { console.error(err); alert('Unable to apply false flag to this proposal.') }
  }

  const handleVetoProposal = async (proposalId: number) => {
    try { await vetoProposal(proposalId); await loadGameState(); await refreshPreview() }
    catch (err) { console.error(err); alert('Unable to veto this proposal (limit reached or already locked).') }
  }

  const activeProposals: Proposal[] = data.proposals || []

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-warroom-blue text-slate-100">
      <div className="crt-overlay" />
      {/* Toast notifications */}
      <div className="fixed top-4 right-4 z-[9998] space-y-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`rounded border px-4 py-2 text-sm shadow-lg backdrop-blur ${
              toast.type === 'error' ? 'border-red-500/50 bg-red-900/80 text-red-200' :
              toast.type === 'warning' ? 'border-warroom-amber/50 bg-yellow-900/80 text-warroom-amber' :
              'border-warroom-cyan/50 bg-slate-900/80 text-warroom-cyan'
            }`}
            onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
          >
            {toast.message}
          </div>
        ))}
      </div>
      {doomActive && <DoomOverlay message={doomMessage} />}
      {escalationFlash && <EscalationAlert flash={escalationFlash} />}
      {crisisFlash && <CrisisAlert crisis={crisisFlash} />}
      <NewsTicker news={newsFeed} />

      {/* Header */}
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
                <div className={`h-2 rounded-full transition-all duration-300 ${timer.state === 'paused' ? 'bg-warroom-amber/70 animate-pulse' : 'bg-warroom-cyan'}`} style={{ width: `${(timerProgress * 100).toFixed(1)}%` }} />
              </div>
              {timer.state === 'paused' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Paused by GM</p>}
              {timer.state === 'complete' && <p className="text-[10px] uppercase tracking-widest text-slate-400">Submissions locked</p>}
              <p className="text-[10px] uppercase tracking-widest text-slate-400">Global Escalation: {totalEscalation}{nextThreshold ? ` → Next at ${nextThreshold}` : ''}</p>
              <DoomsdayClock escalation={totalEscalation} />
            </div>
            <div className="flex gap-2 justify-end">
              <button className="rounded border border-warroom-cyan/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-warroom-cyan hover:border-warroom-cyan" onClick={() => setIsBriefingOpen(true)}>View Briefing</button>
              <button className="rounded border border-warroom-amber/40 bg-warroom-blue/60 px-3 py-1 text-xs font-semibold text-warroom-amber hover:border-warroom-amber" onClick={() => setIsNationsOpen(true)}>Nations Intel</button>
              <button className="rounded-full border border-slate-500 bg-warroom-blue/60 w-7 h-7 flex items-center justify-center text-sm font-bold text-slate-300 hover:border-warroom-cyan hover:text-warroom-cyan" onClick={() => setIsHelpOpen(true)} title="How to Play">?</button>
            </div>
          </div>
        </div>
      </header>

      {isBriefingOpen && <BriefingModal briefing={data.briefing} onClose={() => setIsBriefingOpen(false)} />}
      {isNationsOpen && <NationsModal myTeamId={data.team.id} entries={leaderboard?.entries ?? []} alliances={data.alliances} diplomacyChannels={diplomacyChannels} onClose={() => setIsNationsOpen(false)} />}
      {isHelpOpen && <HowToPlayModal onClose={() => setIsHelpOpen(false)} />}

      <main className="mx-auto grid max-w-6xl gap-6 px-6 py-8 lg:grid-cols-[4fr_1fr]">
        {/* Action Console */}
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
                    <option key={action.code} value={action.code} style={{ color: getCategoryColor(action.category) }}>{action.name}</option>
                  ))}
                </select>
                {actions.find((a) => a.code === selection[slot])?.target_required && (
                  <select className="mt-2 w-full rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-sm disabled:opacity-50" value={targets[slot] ?? ''} onChange={(e) => handleTargetChange(slot, parseInt(e.target.value))} disabled={doomActive}>
                    <option value="">Select target</option>
                    {teamOptions.map((entry) => (
                      <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
                    ))}
                  </select>
                )}
                <button className={`mt-3 w-full rounded border border-slate-600 bg-warroom-blue/60 py-2 text-xs font-bold tracking-wide text-warroom-cyan transition hover:border-warroom-cyan ${doomActive ? 'cursor-not-allowed opacity-50 hover:border-slate-600' : ''}`} onClick={() => handleSubmitProposal(slot)} disabled={doomActive}>Submit Proposal</button>
              </div>
            ))}
          </div>

          {/* Team Proposals */}
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
                        <p className="font-semibold">Slot {proposal.slot}: {actionName(proposal.action_code)}</p>
                        {proposal.target_team_id && <p className="text-xs text-slate-400">Target: {teamOptions.find((t) => t.team_id === proposal.target_team_id)?.nation_name ?? proposal.target_team_id}</p>}
                        {locked && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Locked In</p>}
                        {closed && <p className="text-[10px] uppercase tracking-widest text-slate-400">Closed</p>}
                        {proposal.false_flag_target_team_id && (
                          <p className="text-[10px] uppercase tracking-widest text-warroom-cyan">False flag queued: {teamOptions.find((team) => team.team_id === proposal.false_flag_target_team_id)?.nation_name ?? proposal.false_flag_target_team_id}</p>
                        )}
                        {proposal.status === 'vetoed' && <p className="text-[10px] uppercase tracking-widest text-warroom-amber">Vetoed by Peace Council</p>}
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="rounded border border-slate-600 px-2 text-xs disabled:opacity-40" onClick={() => handleVote(proposal.id, 1)} disabled={votingDisabled}>▲</button>
                        <span className="text-warroom-amber">{totalVotes}</span>
                        <button className="rounded border border-slate-600 px-2 text-xs disabled:opacity-40" onClick={() => handleVote(proposal.id, -1)} disabled={votingDisabled}>▼</button>
                      </div>
                    </div>
                    {!proposal.false_flag_target_team_id && proposal.status === 'draft' && falseFlagCount > 0 && (
                      <div className="mt-2 flex items-center gap-2 text-xs">
                        <select className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1" value={falseFlagTargets[proposal.id] ?? ''} onChange={(e) => setFalseFlagTargets((prev) => ({ ...prev, [proposal.id]: e.target.value === '' ? '' : Number(e.target.value) }))}>
                          <option value="">Select blame nation</option>
                          {teamOptions.map((entry) => (
                            <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
                          ))}
                        </select>
                        <button className="rounded border border-warroom-amber/40 bg-warroom-amber/10 px-3 py-1 text-xs uppercase tracking-widest text-warroom-amber" onClick={() => handleApplyFalseFlag(proposal.id)}>False Flag</button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Intel Drops */}
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
                      <button className="rounded border border-warroom-cyan/40 bg-warroom-cyan/10 px-3 py-1 text-xs uppercase tracking-widest text-warroom-cyan" onClick={() => handleIntelSolve(intel.id)}>Submit</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Lifelines */}
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
            {lifelines.some((l) => l.lifeline_type === 'phone_a_friend' && l.remaining_uses > 0) && (
              <button
                className="mt-2 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1.5 text-xs uppercase tracking-widest text-warroom-amber hover:bg-warroom-amber/20"
                onClick={async () => {
                  try { const result = await usePhoneAFriend(); setPhoneHint(result.hint) }
                  catch { alert('Failed to use Phone-a-Friend.') }
                }}
              >
                Phone-a-Friend
              </button>
            )}
            {phoneHint && (
              <div className="mt-2 rounded border border-warroom-amber/40 bg-warroom-amber/10 p-2 text-xs text-warroom-amber">
                <p className="font-semibold">Intel Received:</p>
                <p>{phoneHint.team_name} is planning <span className="font-bold">{phoneHint.action_name}</span> in slot {phoneHint.slot}</p>
                <button className="mt-1 text-[10px] text-slate-400 underline" onClick={() => setPhoneHint(null)}>Dismiss</button>
              </div>
            )}
          </div>

          {/* Mega Challenge */}
          {megaChallenge?.active && (
            <div className="rounded border border-purple-500/50 bg-purple-900/20 p-4 hack-pulse">
              <h3 className="font-pixel text-xs text-purple-400">Mega Challenge</h3>
              <p className="mt-2 text-xs text-slate-300">{megaChallenge.description}</p>
              <div className="mt-2 text-[10px] text-slate-400">
                Rewards: {(megaChallenge.reward_tiers ?? [15, 10, 5]).map((r, i) => `${i + 1}st +${r}`).join(' | ')} Influence
              </div>
              {megaChallenge.solved_by && megaChallenge.solved_by.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-[10px] text-slate-400">
                  {megaChallenge.solved_by.map((s) => (
                    <li key={s.team_id}>#{s.position} — Team {s.team_id} (+{s.reward})</li>
                  ))}
                </ul>
              )}
              {megaChallenge.already_solved ? (
                <p className="mt-2 text-xs text-green-400">Your team has solved this challenge!</p>
              ) : (
                <div className="mt-2 flex gap-2">
                  <input className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-xs" placeholder="Enter solution..." value={megaAnswer} onChange={(e) => setMegaAnswer(e.target.value)} />
                  <button
                    className="rounded border border-purple-400/40 bg-purple-400/10 px-3 py-1 text-xs uppercase tracking-widest text-purple-400"
                    onClick={async () => {
                      try {
                        const result = await solveMegaChallenge(megaAnswer)
                        alert(`Solved! Position #${result.solve_position}, +${result.reward_influence} Influence`)
                        setMegaAnswer('')
                        const mc = await fetchMegaChallenge()
                        setMegaChallenge(mc)
                      } catch (err: any) {
                        alert(err?.message?.includes('incorrect') ? 'Incorrect solution.' : 'Failed to submit.')
                      }
                    }}
                  >
                    Submit
                  </button>
                </div>
              )}
            </div>
          )}

          {/* UN Peace Council */}
          {isUN && previewData && (
            <div className="rounded border border-slate-700/70 bg-warroom-blue/40 p-4 text-sm text-slate-200">
              <div className="flex items-center justify-between">
                <h3 className="font-pixel text-xs text-warroom-cyan">Peace Council Oversight</h3>
                <p className="text-[10px] uppercase tracking-widest text-slate-400">Vetoes {previewData.vetoes_used}/{previewData.limit}</p>
              </div>
              <div className="mt-3 space-y-3 max-h-56 overflow-y-auto">
                {previewData.teams.map((team) => (
                  <div key={team.team_id} className="rounded border border-slate-700/60 bg-warroom-blue/30 p-2">
                    <p className="text-xs uppercase text-slate-400">{team.nation_name}</p>
                    {team.proposals.map((proposal) => (
                      <div key={proposal.id} className="mt-1 rounded border border-slate-700/50 bg-slate-900/40 p-2 text-xs">
                        <p>Slot {proposal.slot}: {proposal.action_code} ({proposal.status}) — votes {proposal.votes}</p>
                        {proposal.status === 'draft' && !vetoLimitReached && (
                          <button className="mt-1 w-full rounded border border-warroom-amber/40 bg-warroom-amber/10 py-1 text-[10px] uppercase tracking-widest text-warroom-amber" onClick={() => handleVetoProposal(proposal.id)}>Veto Proposal</button>
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

        {/* Sidebar */}
        <aside className="space-y-6">
          {leaderboard && (
            <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 shadow shadow-warroom-cyan/10">
              <h3 className="font-pixel text-xs text-warroom-cyan">Outcome Leaderboard</h3>
              <ul className="mt-3 space-y-2 text-sm">
                {leaderboard.entries.slice(0, 5).map((entry, idx) => (
                  <li key={entry.team_id} className="flex items-center justify-between text-slate-300">
                    <span><span className="mr-2 text-warroom-amber">#{idx + 1}</span>{entry.nation_name}</span>
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

          {/* Roster */}
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4">
            <h3 className="font-pixel text-xs text-warroom-cyan">Team Roster</h3>
            <ul className="mt-2 space-y-1 text-xs text-slate-300">
              {(data as any).roster?.map((member: any) => (
                <li key={member.id} className="flex items-center gap-2">
                  <span className={member.role === 'gm' || member.role === 'admin' ? 'text-red-400' : member.is_captain ? 'text-warroom-amber' : 'text-slate-100'}>
                    {member.display_name}
                  </span>
                  {member.is_captain && <span className="text-[9px] uppercase text-warroom-amber">(Captain)</span>}
                  {(member.role === 'gm' || member.role === 'admin') && <span className="text-[9px] uppercase text-red-400">(GM)</span>}
                </li>
              ))}
            </ul>
          </div>

          {/* Team Chat */}
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 flex flex-col gap-3 min-h-[300px]">
            <div className="flex items-center justify-between">
              <h3 className="font-pixel text-xs text-warroom-cyan">Team Comms</h3>
              <button className="text-[10px] text-slate-400 hover:text-slate-200" onClick={() => setChatCollapsed(!chatCollapsed)}>
                {chatCollapsed ? 'Expand' : 'Collapse'}
              </button>
            </div>
            {!chatCollapsed && (
              <>
                <div className="flex-1 overflow-y-auto rounded border border-slate-700/60 bg-warroom-blue/40 p-3 text-sm text-slate-300 min-h-[200px]">
                  {messages.map((line, idx) => (
                    <p key={idx}>
                      <span className={
                        line.role === 'gm' || line.role === 'admin' ? 'text-red-400 font-semibold' :
                        line.role === 'advisor' ? 'text-warroom-amber' :
                        'text-warroom-cyan'
                      }>{line.display_name}:</span> {line.content}
                    </p>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                {typingUsers.length > 0 && (
                  <p className="text-[10px] text-slate-400 italic">
                    {typingUsers.map((u) => u.display_name).join(', ')} typing...
                  </p>
                )}
                <ChatComposer onSend={sendMessage} onTyping={sendTyping} />
              </>
            )}
          </div>

          {/* Diplomacy */}
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200">
            <h3 className="font-pixel text-xs text-warroom-cyan">Diplomacy</h3>
            <div className="mt-2 flex items-center gap-2">
              <select className="flex-1 rounded border border-slate-700 bg-warroom-blue/60 px-2 py-1 text-xs" value={diplomacyTarget} onChange={(e) => setDiplomacyTarget(Number(e.target.value))}>
                <option value="">Select nation</option>
                {teamOptions.map((entry) => (
                  <option key={entry.team_id} value={entry.team_id}>{entry.nation_name}</option>
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
              <p className="mt-3 text-xs text-slate-400">Human outcome {revealData.human_vs_ai.human_outcome} vs AI outcome {revealData.human_vs_ai.ai_outcome}</p>
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

export default function WrappedApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}

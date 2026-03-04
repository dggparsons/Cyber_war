import { useEffect, useMemo, useState, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'
import {
  fetchGameState,
  fetchSession,
  fetchLeaderboard,
  fetchRevealData,
  fetchActions,
  submitProposal,
  castVote,
  captainOverride,
  ApiError,
  type LeaderboardResponse,
  type RevealData,
  type ActionDefinition,
  type CrisisInfo,
  fetchDiplomacyChannels,
  startDiplomacy,
  sendDiplomacyMessage,
  respondDiplomacy,
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
  type RoundRecap,
  fetchRoundRecap,
} from './lib/api'
import { useChat } from './hooks/useChat'
import { useRoundTimer, type RoundTimer } from './hooks/useRoundTimer'
import { getTeamSocket, getGlobalSocket } from './lib/socket'
import {
  DEFAULT_GLOBAL_STATE,
  formatTimerDisplay,
  type Proposal,
  type GameState,
  type GlobalStatePayload,
} from './lib/gameUtils'

import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthPanel } from './components/AuthPanel'
import { SpectatorView } from './components/SpectatorView'
import { AdminPanel } from './components/AdminPanel'
import { BriefingModal, NationsModal, HowToPlayModal, IntelModal, MegaChallengeModal, RoundRecapModal, type IntelDropItem } from './components/modals'
import { DoomOverlay, CrisisAlert, EscalationAlert } from './components/overlays'
import { NewsTicker } from './components/NewsTicker'
import { GameHeader } from './components/GameHeader'
import { ActionConsole } from './components/ActionConsole'
import { LifelinesPanel } from './components/LifelinesPanel'
import { PeaceCouncilPanel } from './components/PeaceCouncilPanel'
import { GameSidebar } from './components/GameSidebar'
import { AdvisorsPanel } from './components/AdvisorsPanel'
import { ChatComposer } from './components/ChatComposer'

const viewMode = new URLSearchParams(window.location.search).get('view') ?? 'player'

function App() {
  const [data, setData] = useState<GameState | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [authRequired, setAuthRequired] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [globalState, setGlobalState] = useState<GlobalStatePayload | null>(null)
  const chatEnabled = !authRequired && Boolean(data?.team?.id)
  const { messages, sendMessage, typingUsers, sendTyping } = useChat(chatEnabled)
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse | null>(null)
  const [revealData, setRevealData] = useState<RevealData | null>(null)
  const [actions, setActions] = useState<ActionDefinition[]>([])
  const [selection, setSelection] = useState<Record<number, string>>({})
  const [targets, setTargets] = useState<Record<number, number>>({})
  const [timerSeed, setTimerSeed] = useState<RoundTimer>({ round: 1, remaining: 0, duration: 300, state: 'idle' })
  const [isBriefingOpen, setIsBriefingOpen] = useState(false)
  const [isNationsOpen, setIsNationsOpen] = useState(false)
  const [isHelpOpen, setIsHelpOpen] = useState(false)
  const [diplomacyChannels, setDiplomacyChannels] = useState<any[]>([])
  const [diplomacyDrafts, setDiplomacyDrafts] = useState<Record<number, string>>({})
  const [diplomacyTarget, setDiplomacyTarget] = useState<number | ''>('')
  const [diplomacyUnread, setDiplomacyUnread] = useState(0)
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
  const [selectedIntel, setSelectedIntel] = useState<IntelDropItem | null>(null)
  const [isMegaOpen, setIsMegaOpen] = useState(false)
  const [phoneHint, setPhoneHint] = useState<{ team_name: string; action_name: string; slot: number } | null>(null)
  const [roundRecap, setRoundRecap] = useState<RoundRecap | null>(null)
  const [isRecapOpen, setIsRecapOpen] = useState(false)
  const [toasts, setToasts] = useState<Array<{ id: number; message: string; type: 'info' | 'warning' | 'error' }>>([])
  const toastIdRef = useRef(0)
  const addToast = useCallback((message: string, type: 'info' | 'warning' | 'error' = 'info') => {
    const id = ++toastIdRef.current
    setToasts((prev) => [...prev.slice(-4), { id, message, type }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000)
  }, [])
  const [chatCollapsed, setChatCollapsed] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const hasShownBriefingRef = useRef(false)
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
      if (!hasShownBriefingRef.current) {
        hasShownBriefingRef.current = true
        const key = `cyberwar_seen_howtoplay_${gameState.team.id}`
        if (!localStorage.getItem(key)) {
          setIsHelpOpen(true)          // first-ever login for this user → how-to-play first
        } else {
          setIsBriefingOpen(true)      // returning player → straight to briefing
        }
      }
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

  const handleAuthenticated = useCallback(async () => {
    setAuthRequired(false)
    setStatus('loading')
    try {
      const session = await fetchSession()
      if (session.authenticated && session.user?.role && ['admin', 'gm'].includes(session.user.role)) {
        setIsAdmin(true)
        setStatus('ready')
        return
      }
    } catch { /* fall through to loadGameState */ }
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
        if (session.authenticated) {
          if (session.user?.role && ['admin', 'gm'].includes(session.user.role)) {
            setIsAdmin(true)
            setAuthRequired(false)
            setStatus('ready')
          } else {
            setAuthRequired(false)
            loadGameState()
          }
        } else {
          setAuthRequired(true)
          setStatus('ready')
        }
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
    const myTeamId = data.team.id
    const msgHandler = (payload: any) => {
      setDiplomacyChannels((prev) => {
        const copy = prev.map((channel) =>
          channel.channel_id === payload.channel_id
            ? { ...channel, messages: [...channel.messages, { id: payload.id ?? Date.now(), content: payload.content, user_id: payload.team_id, sent_at: payload.sent_at, display_name: payload.display_name }] }
            : channel,
        )
        return copy.length ? copy : prev
      })
      // Toast + badge for messages from other teams
      if (payload.team_id !== myTeamId) {
        const senderName = payload.display_name ?? 'Unknown'
        addToast(`Diplomacy message from ${senderName}`, 'info')
        setDiplomacyUnread((n) => n + 1)
      }
    }
    const channelHandler = (payload: any) => {
      setDiplomacyChannels((prev) => {
        if (prev.some((ch) => ch.channel_id === payload.channel_id)) return prev
        return [...prev, { channel_id: payload.channel_id, status: payload.status ?? 'pending', is_initiator: false, with_team: payload.with_team, messages: [] }]
      })
      if (payload.with_team) {
        addToast(`${payload.with_team.nation_name} opened a diplomacy channel`, 'info')
        setDiplomacyUnread((n) => n + 1)
      }
    }
    const respondHandler = (payload: any) => {
      setDiplomacyChannels((prev) =>
        payload.status === 'declined'
          ? prev.filter((ch) => ch.channel_id !== payload.channel_id)
          : prev.map((ch) => ch.channel_id === payload.channel_id ? { ...ch, status: payload.status } : ch)
      )
      if (payload.status === 'accepted') {
        addToast(`${payload.responded_by} accepted your diplomacy request`, 'info')
      }
    }
    socket.on('diplomacy:message', msgHandler)
    socket.on('diplomacy:channel_opened', channelHandler)
    socket.on('diplomacy:channel_responded', respondHandler)
    return () => { cancelled = true; socket.off('diplomacy:message', msgHandler); socket.off('diplomacy:channel_opened', channelHandler); socket.off('diplomacy:channel_responded', respondHandler) }
  }, [authRequired, data?.team?.id, addToast])

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
      hasShownBriefingRef.current = false
      loadGameState()
    }
    const roundEndedHandler = () => {
      // Round just resolved → fetch recap and show during intermission
      fetchRoundRecap().then((res) => {
        if (res.recap) {
          setRoundRecap(res.recap)
          setIsRecapOpen(true)
        }
      }).catch(console.error)
    }
    const roundStartedHandler = () => {
      // New round timer started → refresh game state for the new round
      loadGameState()
    }
    socket.on('game:nuke_state', nukeHandler)
    socket.on('game:over', doomHandler)
    socket.on('crisis:injected', crisisHandler)
    socket.on('crisis:cleared', crisisClearedHandler)
    socket.on('news:event', newsHandler)
    socket.on('escalation:threshold', escalationHandler)
    socket.on('game:reset', resetHandler)
    socket.on('round:ended', roundEndedHandler)
    socket.on('round:started', roundStartedHandler)
    return () => {
      socket.off('game:nuke_state', nukeHandler)
      socket.off('game:over', doomHandler)
      socket.off('crisis:injected', crisisHandler)
      socket.off('crisis:cleared', crisisClearedHandler)
      socket.off('news:event', newsHandler)
      socket.off('escalation:threshold', escalationHandler)
      socket.off('game:reset', resetHandler)
      socket.off('round:ended', roundEndedHandler)
      socket.off('round:started', roundStartedHandler)
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

  if (viewMode === 'gm' || isAdmin) {
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
  const doomActive = effectiveGlobal.doom_triggered
  const activeCrisis = effectiveGlobal.active_crisis ?? null
  const doomMessage = effectiveGlobal.doom_message ?? 'A catastrophic strike ended the scenario.'

  const handleSelectionChange = (slot: number, value: string) => setSelection((prev) => ({ ...prev, [slot]: value }))
  const handleTargetChange = (slot: number, value: number) => setTargets((prev) => ({ ...prev, [slot]: value }))

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

  const handleRespondDiplomacy = async (channelId: number, action: 'accept' | 'decline') => {
    try {
      await respondDiplomacy(channelId, action)
      const channels = await fetchDiplomacyChannels()
      setDiplomacyChannels(channels)
    } catch (err) { console.error(err); alert('Failed to respond to diplomacy request.') }
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

  const handleMegaSolve = async () => {
    if (!megaAnswer) { alert('Enter a solution attempt first.'); return }
    try {
      const result = await solveMegaChallenge(megaAnswer)
      alert(`Solved! Position #${result.solve_position}, +${result.reward_influence} Influence`)
      setMegaAnswer('')
      const mc = await fetchMegaChallenge()
      setMegaChallenge(mc)
    } catch (err: any) {
      alert(err?.message?.includes('incorrect') ? 'Incorrect solution.' : 'Failed to submit.')
    }
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

  const handleCaptainOverride = async (proposalId: number) => {
    if (doomActive) return
    try { await captainOverride(proposalId); await loadGameState() }
    catch (err) { console.error(err); alert('Unable to lock proposal.') }
  }

  const activeProposals: Proposal[] = data.proposals || []
  const isCaptain = Boolean(data.roster?.find((m) => m.id === (data as any)._userId)?.is_captain) || data.team.role === 'gm' || data.team.role === 'admin'

  // Escalation background tint
  const escalationTint = totalEscalation >= 80 ? 'bg-red-950/30' : totalEscalation >= 60 ? 'bg-red-900/20' : totalEscalation >= 40 ? 'bg-orange-900/15' : ''

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className={`min-h-screen bg-warroom-blue text-slate-100 ${escalationTint}`}>
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

      <GameHeader
        nationName={data.team.nation_name}
        role={data.team.role ?? 'player'}
        connected={connected}
        timer={timer}
        timerDisplay={timerDisplay}
        timerProgress={timerProgress}
        totalEscalation={totalEscalation}
        nextThreshold={nextThreshold}
        megaChallenge={megaChallenge}
        timerState={timer.state}
        onViewBriefing={() => setIsBriefingOpen(true)}
        onViewNations={() => setIsNationsOpen(true)}
        onViewMega={() => setIsMegaOpen(true)}
        onViewHelp={() => setIsHelpOpen(true)}
        onViewRecap={roundRecap ? () => setIsRecapOpen(true) : undefined}
      />

      {isRecapOpen && roundRecap && <RoundRecapModal recap={roundRecap} onClose={() => setIsRecapOpen(false)} />}
      {isBriefingOpen && <BriefingModal briefing={data.briefing} onClose={() => setIsBriefingOpen(false)} />}
      {isNationsOpen && <NationsModal myTeamId={data.team.id} entries={leaderboard?.entries ?? []} alliances={data.alliances} diplomacyChannels={diplomacyChannels} onClose={() => setIsNationsOpen(false)} />}
      {isHelpOpen && <HowToPlayModal onClose={() => {
        setIsHelpOpen(false)
        const key = data ? `cyberwar_seen_howtoplay_${data.team.id}` : ''
        if (key && !localStorage.getItem(key)) {
          localStorage.setItem(key, '1')
          setIsBriefingOpen(true)   // chain into briefing after first how-to-play
        }
      }} />}
      {selectedIntel && (
        <IntelModal
          intel={selectedIntel}
          answer={intelAnswers[selectedIntel.id] ?? ''}
          onAnswerChange={(v) => setIntelAnswers((prev) => ({ ...prev, [selectedIntel.id]: v }))}
          onSubmit={() => { handleIntelSolve(selectedIntel.id); setSelectedIntel(null) }}
          onClose={() => setSelectedIntel(null)}
        />
      )}
      {isMegaOpen && megaChallenge?.active && (
        <MegaChallengeModal
          challenge={megaChallenge}
          answer={megaAnswer}
          onAnswerChange={setMegaAnswer}
          onSubmit={handleMegaSolve}
          onClose={() => setIsMegaOpen(false)}
        />
      )}

      <main className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[3fr_1fr]">
        <div className="space-y-4">
          {/* World News */}
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 text-sm text-slate-200 prose-narrative">
            <h3 className="font-pixel text-xs text-warroom-cyan">World News</h3>
            <div className="mt-2 text-slate-300 leading-relaxed space-y-2 [&_strong]:text-warroom-amber [&_strong]:font-semibold [&_em]:text-slate-400 [&_h2]:font-pixel [&_h2]:text-warroom-amber [&_h2]:text-sm [&_h2]:mt-3 [&_ul]:list-disc [&_ul]:pl-4 [&_li]:text-slate-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.narrative}</ReactMarkdown>
            </div>
          </div>

          <ActionConsole
            nukeUnlocked={nukeUnlocked}
            doomActive={doomActive}
            activeCrisis={activeCrisis}
            availableActions={availableActions}
            actions={actions}
            activeProposals={activeProposals}
            selection={selection}
            targets={targets}
            teamOptions={teamOptions}
            falseFlagCount={falseFlagCount}
            falseFlagTargets={falseFlagTargets}
            isCaptain={isCaptain}
            onSelectionChange={handleSelectionChange}
            onTargetChange={handleTargetChange}
            onSubmitProposal={handleSubmitProposal}
            onVote={handleVote}
            onApplyFalseFlag={handleApplyFalseFlag}
            onFalseFlagTargetChange={(pid, val) => setFalseFlagTargets((prev) => ({ ...prev, [pid]: val }))}
            onCaptainOverride={handleCaptainOverride}
          />

          {/* Team Chat — full width under action console */}
          <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-4 flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <h3 className="font-pixel text-xs text-warroom-cyan">Team Comms</h3>
              <button className="text-[10px] text-slate-400 hover:text-slate-200" onClick={() => setChatCollapsed(!chatCollapsed)}>
                {chatCollapsed ? 'Expand' : 'Collapse'}
              </button>
            </div>
            {!chatCollapsed && (
              <>
                <div className="overflow-y-auto rounded border border-slate-700/60 bg-warroom-blue/40 p-3 text-sm text-slate-300 max-h-48 min-h-[120px]">
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

          <AdvisorsPanel advisors={data.advisors} />

          <LifelinesPanel
            lifelines={lifelines}
            phoneHint={phoneHint}
            onUsePhoneAFriend={async () => {
              try { const result = await usePhoneAFriend(); setPhoneHint(result.hint) }
              catch { alert('Failed to use Phone-a-Friend.') }
            }}
            onDismissHint={() => setPhoneHint(null)}
          />

          {isUN && previewData && (
            <PeaceCouncilPanel previewData={previewData} onVetoProposal={handleVetoProposal} />
          )}
        </div>

        <GameSidebar
          data={data}
          leaderboard={leaderboard}
          historyEntries={historyEntries}
          intel={{
            drops: data.intel_drops,
            megaChallenge,
            onSelectIntel: setSelectedIntel,
            onOpenMega: () => setIsMegaOpen(true),
          }}
          shouldShowReveal={shouldShowReveal}
          revealData={revealData}
          diplomacy={{
            teamId: data.team.id,
            channels: diplomacyChannels,
            drafts: diplomacyDrafts,
            target: diplomacyTarget,
            unread: diplomacyUnread,
            teamOptions,
            alliances: data.alliances,
            leaderboard,
            onTargetChange: (val) => setDiplomacyTarget(val),
            onStart: handleStartDiplomacy,
            onSend: handleSendDiplomacy,
            onDraftChange: (channelId, val) => setDiplomacyDrafts((prev) => ({ ...prev, [channelId]: val })),
            onRespond: handleRespondDiplomacy,
            onClick: () => setDiplomacyUnread(0),
          }}
        />
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

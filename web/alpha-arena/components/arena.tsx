"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { acceptsRoomState, publicRoundView, remoteDisplayIndices, roomPollIntervalMs, sameActionContext } from "./arena-state.mjs";
import { engineStatus } from "./engine-status.mjs";
import { clockSample } from "./server-clock.mjs";
import { clearRemoteSessions, currentSessionRequest, resetSessionFailure, sessionKey } from "./arena-session.mjs";
import { ArrowRight, Bot, Check, CheckCheck, ChevronRight, CircleHelp, Clock3, Copy, Flag, Image as ImageIcon, Link2, LoaderCircle, LockKeyhole, Radio, ShieldCheck, Sparkles, Timer, Trophy, UserRound, UsersRound, X } from "lucide-react";

type Role = "human" | "bot";
type Lane = "A" | "B";
type Mode = "remote" | "legacy";
type RemoteState = {
  mode: "remote"; lane: Lane; viewerConnected: boolean; engineConnected: boolean;
  engineStage: string;
  engineHeartbeatReceived?: boolean;
  gpuReservationSupported?: boolean;
  imageBarrierSupported?: boolean;
  selectionPlanSupported?: boolean;
  selectionPlan?: { roundId: string; selectedIndices: number[]; startAt: number; intervalMs: number; submitAt: number };
  selectedIndices?: number[]; sequence: number; lastSelectionAt: number | null;
};
type PlayerState = { ready: boolean; submitted: boolean; correct: boolean | null; elapsedMs: number | null };
type RoomState = {
  revision?: number;
  serverNow: number; roomId: string; code: string; phase: "lobby" | "queued" | "loading" | "countdown" | "playing" | "result";
  roundId: string | null; roundNumber: number; startAt: number | null; deadlineAt: number | null;
  startRequest?: { id: string; requestedAt: number; expiresAt: number } | null;
  lastStartCancellationReason?: "human_cancelled" | "engine_disconnected" | "engine_error" | "queue_expired" | "image_load_failed" | "image_load_timeout" | null;
  imageLoad?: { id: string; expiresAt: number; humanReady: boolean; botReady: boolean; engineReady: boolean };
  preloadTiles?: { id: string; url: string }[];
  preloadTopic?: { id: string; prompt: string; condition: Record<string, unknown> };
  topic: { id: string; prompt: string; condition: Record<string, unknown> } | null;
  tiles: { id: string; url: string }[]; human: PlayerState; bot: PlayerState;
  result: { winner: Role | null; finishedAt?: number | null; elapsedMs?: number | null; reason?: "correct" | "timeout" | null } | null;
  remote?: RemoteState;
};
type Session = { roomId: string; code: string; token: string };
type RoomResponse = RoomState | { state: RoomState; correct?: boolean; elapsedMs?: number };

function roomFrom(data: RoomResponse): RoomState {
  return "state" in data ? data.state : data;
}

type SessionRequest = { generation: number; roomId: string | null; storageKey: string };

class ApiFailure extends Error {
  constructor(message: string, readonly status: number, readonly code?: string) { super(message); }
}
async function api<T>(path: string, token?: string, payload?: unknown): Promise<{ data: T; before: number; after: number }> {
  const before = performance.now();
  const response = await fetch(path, {
    method: payload === undefined ? "GET" : "POST", cache: "no-store",
    signal: AbortSignal.timeout(10_000),
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(payload === undefined ? {} : { "Content-Type": "application/json" }) },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const failure = data as { error?: string | { message?: string }; code?: string } | null;
    const message = typeof failure?.error === "string" ? failure.error : failure?.error?.message;
    throw new ApiFailure(message || `요청을 처리하지 못했습니다. (${response.status})`, response.status, failure?.code);
  }
  return { data: data as T, before, after: performance.now() };
}

export function BrandHeader({ role, admin = false }: { role?: Role; admin?: boolean }) {
  return <header className="topbar">
    <Link className="brand" href="/" aria-label="알파 아레나 홈"><span className="brand-mark">α</span><div><div className="brand-title">ALPHA <span>ARENA</span></div><div className="brand-subtitle">Human instinct. Artificial intelligence.</div></div></Link>
    <nav className="nav-links" aria-label="메인"><Link className="nav-link" href="/#how-to-play">대결 안내</Link><Link className="nav-link" href="/admin">사진 관리 <ArrowRight size={12} style={{ display: "inline", marginLeft: 3 }} /></Link><span className="live-pill"><span className="live-dot" />{admin ? "관리자 스튜디오" : role === "bot" ? "AI 플레이어" : "송내고등학교 · 알파"}</span></nav>
  </header>;
}

export default function Arena() {
  const [role, setRole] = useState<Role>("human");
  const [mode, setMode] = useState<Mode>("remote");
  const [lane, setLane] = useState<Lane>("A");
  const [session, setSession] = useState<Session | null>(null);
  const [state, setState] = useState<RoomState | null>(null);
  const [code, setCode] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loaded, setLoaded] = useState<Set<string>>(new Set());
  const [imageError, setImageError] = useState(false);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState("");
  const [now, setNow] = useState(0);
  const [copied, setCopied] = useState(false);
  const [connected, setConnected] = useState(false);
  const [clockOffset, setClockOffset] = useState(0);
  const clockEstimate = useRef<{ offset: number; rtt: number; sampledAt: number } | null>(null);
  const [pageVisible, setPageVisible] = useState(true);
  const hiddenResetRound = useRef<string | null>(null);
  const acceptedState = useRef<RoomState | null>(null);
  const roundRef = useRef<string | null>(null);
  const activeRoom = useRef<string | null>(null);
  const activeLane = useRef<Lane>("A");
  const storageKey = useRef("alpha-arena-human-remote-A");
  const imageMount = useRef<string | null>(null);
  const imageAck = useRef<string | null>(null);
  const [registeredImageRound, setRegisteredImageRound] = useState<string | null>(null);
  const sessionGeneration = useRef(0);
  const busyRequest = useRef<symbol | null>(null);

  const requestContext = useCallback((): SessionRequest => ({ generation: sessionGeneration.current,
    roomId: activeRoom.current, storageKey: storageKey.current }), []);
  const requestIsCurrent = useCallback((request: SessionRequest) => currentSessionRequest(request, requestContext()), [requestContext]);
  const resetSession = useCallback((message = "") => {
    sessionGeneration.current += 1;
    activeRoom.current = null; acceptedState.current = null; roundRef.current = null;
    clockEstimate.current = null; imageMount.current = null; imageAck.current = null; hiddenResetRound.current = null;
    busyRequest.current = null;
    try { sessionStorage.removeItem(storageKey.current); } catch { /* Keep the in-memory session cleared when storage is unavailable. */ }
    setSession(null); setState(null); setSelected(new Set()); setLoaded(new Set()); setImageError(false);
    setRegisteredImageRound(null); setClockOffset(0); setNow(performance.now()); setConnected(false);
    setBusy(""); setFeedback(""); setCode(""); setCopied(false); setError(message);
  }, []);
  const recoverSession = useCallback((failure: unknown, request: SessionRequest) => {
    if (!resetSessionFailure(failure, request, requestContext())) return false;
    resetSession(failure instanceof ApiFailure && failure.code === "room_reset"
      ? "운영 준비가 초기화됐어요. 새 대결방을 만들거나 새 연결 코드를 입력해 주세요."
      : "대기실이 만료됐어요. 새 대결방을 만들거나 새 연결 코드를 입력해 주세요.");
    return true;
  }, [requestContext, resetSession]);

  const receive = useCallback((next: RoomState, before: number, after: number) => {
    if (!next || next.roomId !== activeRoom.current || !acceptsRoomState(acceptedState.current, next)) return false;
    if (next.remote && next.remote.lane !== activeLane.current) {
      setConnected(false); setError("다른 구역의 대결입니다. 연결 코드를 다시 확인해 주세요."); return false;
    }
    const previous = acceptedState.current;
    acceptedState.current = next;
    const fixedCountdown = previous?.phase === "countdown" && next.phase === "countdown"
      && previous.imageLoad?.id === next.imageLoad?.id && previous.startAt === next.startAt;
    clockEstimate.current = clockSample(clockEstimate.current, next.serverNow, before, after, fixedCountdown);
    setClockOffset(clockEstimate.current?.offset ?? 0);
    if (roundRef.current !== next.roundId || previous?.startRequest?.id !== next.startRequest?.id) {
      roundRef.current = next.roundId;
      setSelected(new Set()); setLoaded(new Set()); setImageError(false); setFeedback(""); setError("");
    }
    if (next.phase === "result") setFeedback("");
    setState(next); setConnected(true); setNow(performance.now());
    return true;
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const explicitReset = params.get("reset") === "1";
    const detected: Role = params.get("role") === "bot" || window.location.hostname.startsWith("bot.") ? "bot" : "human";
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const roomId = explicitReset ? null : fragment.get("room"); const token = explicitReset ? null : fragment.get("token");
    const detectedMode: Mode = params.get("mode") === "legacy" || (roomId && token && params.get("mode") !== "remote") ? "legacy" : "remote";
    let savedLane: string | null = null;
    try { savedLane = localStorage.getItem(`alpha-arena-lane-${detected}`); } catch { /* The URL still identifies the pad when storage is unavailable. */ }
    const requestedLane = params.get("lane")?.toUpperCase();
    const detectedLane: Lane = requestedLane === "A" || requestedLane === "B" ? requestedLane : savedLane === "B" ? "B" : "A";
    activeLane.current = detectedLane;
    storageKey.current = sessionKey(detected, detectedMode, detectedLane);
    if (explicitReset) {
      try { clearRemoteSessions(sessionStorage); } catch { /* Reset memory even if browser storage is unavailable. */ }
      resetSession();
      params.delete("reset");
    }
    let restored: Session | null = null;
    if (!explicitReset && roomId && token) {
      const next = { roomId, token, code: "" };
      sessionStorage.setItem(storageKey.current, JSON.stringify(next));
      restored = next;
    } else if (!explicitReset) {
      try {
        const stored = sessionStorage.getItem(storageKey.current);
        const parsed: Session | null = stored ? JSON.parse(stored) : null;
        if (parsed && typeof parsed.roomId === "string" && typeof parsed.token === "string") restored = parsed;
      } catch { sessionStorage.removeItem(storageKey.current); }
    }
    // A runner hands the role token to this tab once; never retain it in the URL.
    params.set("lane", detectedLane);
    if (detectedMode === "legacy") params.set("mode", "legacy");
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
    const visibility = () => setPageVisible(document.visibilityState === "visible");
    visibility(); document.addEventListener("visibilitychange", visibility);
    const initialize = window.setTimeout(() => { activeRoom.current = restored?.roomId || null; setRole(detected); setMode(detectedMode); setLane(detectedLane); setSession(restored); setNow(performance.now()); }, 0);
    const ticker = window.setInterval(() => setNow(performance.now()), 50);
    return () => { window.clearTimeout(initialize); window.clearInterval(ticker); document.removeEventListener("visibilitychange", visibility); };
  }, [resetSession]);

  useEffect(() => {
    document.title = role === "bot" ? `ALPHA BOT | CAPTCHA · ${lane} 구역` : `ALPHA ARENA · 인간 vs AI · ${lane} 구역`;
  }, [role, lane]);

  const pollIntervalMs = roomPollIntervalMs(role, state);

  useEffect(() => {
    if (!session) return;
    const request = requestContext();
    let stopped = false;
    let inFlight = false;
    const poll = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const result = await api<RoomResponse>(`/api/rooms/${encodeURIComponent(session.roomId)}`, session.token);
        if (!stopped && requestIsCurrent(request)) receive(roomFrom(result.data), result.before, result.after);
      } catch (failure) {
        if (stopped || !requestIsCurrent(request) || recoverSession(failure, request)) return;
        const changed = failure instanceof ApiFailure && failure.status === 409
          && ["room_changed", "round_changed", "engine_state_changed", "start_request_changed", "image_load_changed"].includes(failure.code ?? "");
        if (!changed && !stopped && activeRoom.current === session.roomId) { setConnected(false); setError(failure instanceof Error ? failure.message : "서버 연결을 확인해 주세요."); }
      }
      finally { inFlight = false; }
    };
    void poll();
    const interval = window.setInterval(poll, pollIntervalMs);
    return () => { stopped = true; window.clearInterval(interval); };
  }, [session, receive, pollIntervalMs, requestContext, requestIsCurrent, recoverSession]);

  // Legacy rounds still need the question at start. Prepared remote rounds
  // reveal the existing pixels/prompt on the local common clock without HTTP.
  useEffect(() => {
    if (!session || state?.phase !== "countdown" || !state.startAt || state.imageLoad) return;
    const request = requestContext();
    let stopped = false;
    const open = window.setTimeout(async () => {
      try {
        const result = await api<RoomResponse>(`/api/rooms/${encodeURIComponent(session.roomId)}`, session.token);
        if (!stopped && requestIsCurrent(request)) receive(roomFrom(result.data), result.before, result.after);
      } catch (failure) { if (!stopped) recoverSession(failure, request); }
    }, Math.max(0, state.startAt - performance.now() - clockOffset + 10));
    return () => { stopped = true; window.clearTimeout(open); };
  }, [session, state?.phase, state?.startAt, state?.imageLoad, clockOffset, receive, requestContext, requestIsCurrent, recoverSession]);

  const saveSession = (next: Session, nextState: RoomState, before: number, after: number) => {
    if (nextState.remote && nextState.remote.lane !== lane) throw new Error(`${lane} 구역 코드가 아닙니다. 인간 화면의 구역과 코드를 확인해 주세요.`);
    const nextMode: Mode = nextState.remote ? "remote" : "legacy";
    setMode(nextMode);
    activeLane.current = lane;
    storageKey.current = sessionKey(role, nextMode, lane);
    sessionGeneration.current += 1;
    activeRoom.current = next.roomId;
    acceptedState.current = null;
    clockEstimate.current = null;
    sessionStorage.setItem(storageKey.current, JSON.stringify({ roomId: next.roomId, code: next.code, token: next.token }));
    setSession({ roomId: next.roomId, code: next.code, token: next.token });
    receive(nextState, before, after);
  };

  const act = async (action: string) => {
    if (busyRequest.current) return;
    if (role === "bot" && state?.remote && (action === "ready" || action === "submit" || action === "next" || action === "cancel-start" || action === "start")) return;
    if (action === "next" && (role !== "human" || !state?.remote || state.phase !== "result" || !state.roundId)) return;
    if (action === "cancel-start" && (role !== "human" || !state?.remote || !["queued", "loading", "countdown"].includes(state.phase) || !state.startRequest)) return;
    if (action === "start" && state?.remote && (state.phase !== "lobby" || state.remote.gpuReservationSupported !== true || state.remote.imageBarrierSupported !== true)) return;
    if (action === "new-participant") resetSession();
    const source = acceptedState.current, request = requestContext(), busyToken = Symbol(action);
    busyRequest.current = busyToken;
    setBusy(action); setError("");
    if (action === "submit") setFeedback("");
    try {
      if (action === "create" || action === "join" || action === "new-participant") {
        const create = action !== "join";
        const result = await api<Session & { state: RoomState }>(create ? "/api/rooms" : "/api/rooms/join", undefined, create ? mode === "remote" ? { mode: "remote", lane } : {} : { code: code.trim().toUpperCase(), role: "bot", ...(mode === "remote" ? { lane } : {}) });
        if (requestIsCurrent(request)) saveSession(result.data, result.data.state, result.before, result.after);
      } else if (session) {
        const payload = action === "ready" ? { ready: true } : action === "submit" ? { roundId: state?.roundId, tileIds: [...selected] } : action === "next" ? { roundId: state?.roundId } : action === "cancel-start" ? { requestId: state?.startRequest?.id } : action === "start" && state?.remote ? { expectedRevision: state.revision } : {};
        const result = await api<RoomResponse>(`/api/rooms/${encodeURIComponent(session.roomId)}/${action}`, session.token, payload);
        const accepted = requestIsCurrent(request) && receive(roomFrom(result.data), result.before, result.after);
        if (accepted && action === "submit" && "state" in result.data && result.data.correct === false && result.data.state.phase === "playing") {
          setFeedback("아직 정답이 아니에요. 사진을 수정해서 다시 제출하세요. 시간은 계속 흐릅니다.");
        }
      }
    } catch (failure) {
      if (!requestIsCurrent(request) || recoverSession(failure, request)) return;
      const sessionAction = action !== "create" && action !== "join" && action !== "new-participant";
      if (!sessionAction || activeRoom.current === source?.roomId && sameActionContext(source, acceptedState.current)) setError(failure instanceof Error ? failure.message : "요청 중 오류가 발생했습니다.");
    }
    finally { if (busyRequest.current === busyToken) { busyRequest.current = null; setBusy(""); } }
  };

  const leave = () => {
    resetSession();
  };
  const chooseLane = (next: Lane) => {
    if (session || busyRequest.current) return;
    setLane(next); activeLane.current = next; setError(""); setCode("");
    storageKey.current = sessionKey(role, mode, next);
    try { localStorage.setItem(`alpha-arena-lane-${role}`, next); } catch { /* The URL is also persistent across reloads. */ }
    const params = new URLSearchParams(window.location.search); params.set("lane", next);
    window.history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`);
  };
  const remote = state?.remote;
  const remoteMode = mode === "remote";
  const viewer = role === "bot" && remoteMode;
  const serverNow = now + clockOffset;
  const roundView = publicRoundView(state, serverNow);
  const queued = roundView.queued;
  const loadingImages = roundView.loading;
  const waitingForStart = queued || loadingImages;
  const needsEngineUpdate = !!remote && remote.engineHeartbeatReceived === true && (remote.gpuReservationSupported !== true || remote.imageBarrierSupported !== true);
  const started = !!roundView.startAt && serverNow >= roundView.startAt;
  const deadlineReached = !!roundView.deadlineAt && serverNow >= roundView.deadlineAt;
  const playing = !!state && (state.phase === "playing" || state.phase === "countdown") && started && !deadlineReached;
  const countdown = !!roundView.startAt && !started && (state?.phase === "countdown" || state?.phase === "playing");
  const tiles = roundView.tiles;
  const imagesReady = tiles.length === 9 && loaded.size === 9 && !imageError;
  // Local answer editing does not wait for a poll or submission round trip.
  // Every submission still receives authoritative server grading.
  const canSelect = !viewer && playing && imagesReady;
  const visibleSelected = queued ? new Set<string>() : viewer ? new Set(remoteDisplayIndices(state, serverNow).map((index: number) => tiles[index]?.id).filter((id: string | undefined): id is string => !!id)) : selected;
  const canStart = !!state?.bot.ready && (!remote || remote.gpuReservationSupported === true && remote.imageBarrierSupported === true && Number.isInteger(state?.revision) && remote.viewerConnected && remote.engineConnected && remote.engineStage === "ready");
  // A fresh page invalidates old readiness once. Concurrent mounts that lose
  // the epoch CAS fetch the winning epoch rather than resetting it in a loop.
  useEffect(() => {
    if (!session || !state?.imageLoad || !state.roundId || !state.startRequest
      || !["loading", "countdown"].includes(state.phase) || imageMount.current === state.roundId) return;
    const snapshot = state, roundId = state.roundId, request = requestContext();
    imageMount.current = roundId; imageAck.current = null;
    void (async () => {
      let confirmed = false;
      try {
        const result = await api<RoomResponse>(`/api/rooms/${session.roomId}/images-ready`, session.token,
          { roundId, requestId: snapshot.startRequest!.id, imageLoadId: snapshot.imageLoad!.id, ready: false });
        if (requestIsCurrent(request)) receive(roomFrom(result.data), result.before, result.after);
        confirmed = true;
      } catch (failure) {
        if (!requestIsCurrent(request) || recoverSession(failure, request)) return;
        try {
          const result = await api<RoomResponse>(`/api/rooms/${session.roomId}`, session.token);
          const latest = roomFrom(result.data);
          // A concurrent mount (or our lost response) must have actually
          // changed the epoch before this page can reuse its registration.
          confirmed = latest.roundId === roundId && !!latest.imageLoad
            && latest.imageLoad.id !== snapshot.imageLoad!.id;
          if (requestIsCurrent(request)) receive(latest, result.before, result.after);
        } catch (failure) { recoverSession(failure, request); }
      } finally {
        if (requestIsCurrent(request) && roundRef.current === roundId) {
          if (confirmed) setRegisteredImageRound(roundId);
          else imageMount.current = null;
        }
      }
    })();
  }, [session, state, receive, requestContext, requestIsCurrent, recoverSession]);
  useEffect(() => {
    if (!session || !state?.imageLoad || !state.roundId || registeredImageRound !== state.roundId || !state.startRequest
      || !["loading", "countdown"].includes(state.phase) || !pageVisible || !imagesReady && !imageError) return;
    const key = `${state.roundId}:${state.imageLoad.id}:${imageError ? "failed" : "ready"}`;
    if (imageAck.current === key) return;
    const request = requestContext();
    imageAck.current = key;
    void api<RoomResponse>(`/api/rooms/${session.roomId}/images-ready`, session.token,
      { roundId: state.roundId, requestId: state.startRequest.id, imageLoadId: state.imageLoad.id, ready: !imageError, failed: imageError })
      .then(result => { if (requestIsCurrent(request)) receive(roomFrom(result.data), result.before, result.after); })
      .catch(failure => { if (requestIsCurrent(request) && !recoverSession(failure, request) && imageAck.current === key) imageAck.current = null; });
  }, [session, state, registeredImageRound, imagesReady, imageError, pageVisible, receive, requestContext, requestIsCurrent, recoverSession]);
  // A backgrounded browser cannot promise a visible common start. Withdraw
  // its readiness once per hidden period, and re-ACK the same decoded images
  // when visible again. The server rejects withdrawals after actual start.
  useEffect(() => {
    if (pageVisible) { hiddenResetRound.current = null; return; }
    if (!session || !state?.imageLoad || !state.roundId || !state.startRequest
      || !["loading", "countdown"].includes(state.phase) || hiddenResetRound.current === state.roundId) return;
    const request = requestContext();
    hiddenResetRound.current = state.roundId; imageAck.current = null;
    void api<RoomResponse>(`/api/rooms/${session.roomId}/images-ready`, session.token,
      { roundId: state.roundId, requestId: state.startRequest.id, imageLoadId: state.imageLoad.id, ready: false })
      .then(result => { if (requestIsCurrent(request)) receive(roomFrom(result.data), result.before, result.after); })
      .catch(failure => { if (requestIsCurrent(request) && !recoverSession(failure, request) && hiddenResetRound.current === state.roundId) hiddenResetRound.current = null; });
  }, [session, state, pageVisible, receive, requestContext, requestIsCurrent, recoverSession]);
  const winner = state?.result?.winner;
  const winningElapsed = winner === "human" || winner === "bot" ? state?.[winner].elapsedMs : null;
  const finalElapsed = state?.result?.elapsedMs ?? winningElapsed ?? (state?.startAt && state.deadlineAt ? state.deadlineAt - state.startAt : 0);
  const elapsed = roundView.startAt ? Math.max(0, state?.phase === "result" ? finalElapsed : Math.min(serverNow, roundView.deadlineAt ?? serverNow) - roundView.startAt) : 0;
  const timer = (elapsed / 1000).toFixed(2);
  const resultTitle = winner === "human" ? "인간의 승리!" : winner === "bot" ? "AI의 승리!" : "시간 종료 · 승자 없음";
  const playerStatus = (player?: PlayerState, playerRole: Role = "human") => {
    if (state?.phase === "result") return player?.correct ? "먼저 정답!" : "대결 종료";
    if (waitingForStart && playerRole === "human") return "출발 대기 · 타이머 정지";
    if (playerRole === "bot" && remote) return !connected ? "연결 확인 중" : engineStatus(remote, player);
    // The server's ready flag belongs to this browser role, not the PC model.
    if (playerRole === "bot") return playing ? "봇 화면 진행 중" : player?.ready ? "봇 화면 준비" : "봇 화면 연결 대기";
    return playing ? player?.correct === false ? "선택을 수정하고 있어요" : "문제를 풀고 있어요" : player?.ready ? "준비 완료" : "입장 대기";
  };
  const roomCode = state?.code || session?.code || "--------";
  const nextParticipantAction = remote ? "next" : "new-participant";
  const nextParticipantLabel = remote ? "다음 참가자 준비" : "새 참가자 대결 만들기";
  const cancellationMessages = { human_cancelled: "출발 대기를 취소했어요. 준비되면 다시 시작하세요.", engine_disconnected: "PC 봇 연결이 끊겨 출발 대기가 취소됐어요. 연결을 확인한 뒤 다시 시작하세요.", engine_error: "PC 봇 오류로 출발 대기가 취소됐어요. 운영자가 확인한 뒤 다시 시작하세요.", queue_expired: "출발 대기 시간이 지나 취소됐어요. PC 봇 준비를 확인한 뒤 다시 시작하세요.", image_load_failed: "사진을 불러오지 못해 출발을 취소했어요. 연결을 확인하고 다시 시작하세요.", image_load_timeout: "사진 준비 시간이 지나 출발을 취소했어요. 연결을 확인하고 다시 시작하세요." };
  const cancellationMessage = state?.phase === "lobby" && state.lastStartCancellationReason ? cancellationMessages[state.lastStartCancellationReason] : null;
  const laneSelector = !session && remoteMode && <fieldset className="lane-picker"><legend>이 화면의 구역을 선택하세요</legend><div>{(["A", "B"] as Lane[]).map(item => <button type="button" key={item} className={lane === item ? "lane-option active" : "lane-option"} aria-pressed={lane === item} disabled={!!busy} onClick={() => chooseLane(item)}><strong>{item}</strong><span>{item} 구역</span></button>)}</div><p>한 대결의 인간 화면과 AI 표시 화면을 같은 구역으로 맞추세요.</p></fieldset>;

  const roomCard = <section className="side-card room-card" aria-labelledby="room-title">
    <div className="side-heading"><h2 id="room-title">{session ? `${remote ? `${remote.lane} 구역 · ` : ""}대결 준비실` : role === "bot" ? "AI 표시 화면 연결" : "오늘의 도전자, 당신"}</h2><span className="step-index">{remoteMode ? `${lane} 구역` : session ? "CONNECTED" : "GET READY"}</span></div>
    {!session ? <>
      <p>{role === "human" ? "대결방을 만들고 AI 표시 화면과 PC 봇에 연결 코드를 알려 주세요." : "연결할 인간 화면의 구역과 코드를 확인하세요. AI는 PC에서 실행됩니다."}</p>
      {laneSelector}
      {role === "bot" && <form onSubmit={event => { event.preventDefault(); void act("join"); }}><div className="field"><label htmlFor="pair-code">{remoteMode ? `${lane} 구역 · ` : ""}8자리 연결 코드</label><input id="pair-code" className="input code-input" value={code} onChange={event => setCode(event.target.value.replace(/[^a-z0-9]/gi, "").slice(0, 8))} maxLength={8} autoComplete="off" spellCheck={false} placeholder="ABCD2345" required /></div><button className="btn primary block" disabled={!!busy || code.trim().length !== 8}>{busy === "join" ? <LoaderCircle className="spinner" size={16} /> : <Link2 size={16} />}{remoteMode ? `${lane} 구역 표시 연결` : "대결 연결하기"}</button></form>}
      {role === "human" && <button className="btn primary block" onClick={() => void act("create")} disabled={!!busy}>{busy === "create" ? <LoaderCircle className="spinner" size={16} /> : <Flag size={16} />}{remoteMode ? `${lane} 구역 새 대결 만들기` : "새 대결 만들기"}<ArrowRight size={15} /></button>}
      <p className="status-note">사진 문제은행이 준비되어 있어야 시작할 수 있어요.</p>
    </> : state?.phase === "result" ? <>
      <p>{remote ? "한 참가자의 대결이 끝났습니다. 다음 참가자를 준비해도 이 방의 코드와 AI 연결은 그대로 유지됩니다." : "한 참가자의 대결이 끝났습니다. 새 참가자는 새 대결방에서 시작하며 AI도 새 코드로 다시 연결해야 합니다."}</p>
      {role === "human" ? <button className="btn primary block" disabled={!!busy || !!remote && !connected} onClick={() => void act(nextParticipantAction)}>{busy === nextParticipantAction ? <LoaderCircle className="spinner" size={16} /> : <UsersRound size={16} />}{nextParticipantLabel}</button> : remote ? <p className="status-note" role="status">다음 참가자 대기 · 연결 유지</p> : <button className="btn primary block" disabled={!!busy} onClick={leave}><Link2 size={16} />새 코드로 연결하기</button>}
      <p className="status-note">{remote ? "인간 화면에서 다음 참가자를 준비하고, PC 봇 준비가 끝나면 다시 시작하세요." : "이 대결방에서 다음 문제를 시작하지 않습니다."}</p>
    </> : <>
      <p>{remote ? `${remote.lane} 구역 AI 표시 화면과 PC 봇은 처음 한 번 같은 코드로 연결하세요. 참가자가 바뀌어도 방과 연결은 유지됩니다.` : "봇을 실행할 PC와 연결 코드를 공유하세요."}</p>
      <div className="room-code" aria-label={`연결 코드 ${roomCode}`}>{roomCode}</div>
      <button className="btn small block" onClick={async () => { try { await navigator.clipboard.writeText(roomCode); setCopied(true); window.setTimeout(() => setCopied(false), 1500); } catch { setError("연결 코드를 직접 입력해 주세요."); } }}>{copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "코드를 복사했어요" : "연결 코드 복사"}</button>
      <div style={{ marginTop: 13 }}><div className="connection-row"><span>인간 플레이어</span><span className="connected"><CheckCheck size={12} />방 생성 완료</span></div>{remote ? <><div className="connection-row"><span>AI 표시 화면</span><span className={remote.viewerConnected ? "connected" : "waiting"}>{remote.viewerConnected ? <><CheckCheck size={12} />연결 등록됨</> : "코드 연결 대기"}</span></div><div className="connection-row"><span>PC 봇</span><span className={remote.engineConnected && remote.engineStage !== "error" ? "connected" : "waiting"}>{connected ? engineStatus(remote, state?.bot) : "연결 확인 중"}</span></div></> : <div className="connection-row"><span>봇 화면</span><span className={state?.bot.ready ? "connected" : "waiting"}>{state?.bot.ready ? <><CheckCheck size={12} />화면 준비됨</> : "화면 준비 대기"}</span></div>}</div>
      <div className="sidebar-actions">
        {role === "human" && ((waitingForStart || countdown) ? <button className="btn primary block" disabled={!!busy || !connected} onClick={() => void act("cancel-start")}>{busy === "cancel-start" ? <LoaderCircle className="spinner" size={16} /> : <X size={16} />}출발 대기 취소</button> : <button className="btn primary block" disabled={!canStart || !!busy || !connected || state?.phase !== "lobby"} onClick={() => void act("start")}>{busy === "start" ? <LoaderCircle className="spinner" size={16} /> : <ArrowRight size={16} />}대결 시작하기</button>)}
        {role === "bot" && !remote && <button className="btn primary block" disabled={!!state?.bot.ready || !!busy || !connected} onClick={() => void act("ready")}>{state?.bot.ready ? <Check size={16} /> : <Radio size={16} />}{state?.bot.ready ? "봇 화면 준비" : "봇 화면 준비 알리기"}</button>}
        <button className="btn text" onClick={leave} disabled={!!busy || waitingForStart || countdown}>준비실 나가기</button>
      </div>{needsEngineUpdate && state?.phase === "lobby" && <p className="status-note" role="status">새 대결을 시작하려면 PC 봇 실행기를 업데이트하고 재시작해 주세요.</p>}{cancellationMessage && <p className="status-note" role="status">{cancellationMessage}</p>}<p className="status-note">{connected ? "서버와 연결되어 있어요 · 상태를 주기적으로 갱신" : "서버 연결을 다시 확인하고 있어요"}</p>
    </>}
    <p className="status-note">{remoteMode ? "AI는 PC에서 실행됩니다. AI 표시 화면은 PC의 선택만 보여주며 브라우저를 대신 클릭하지 않습니다." : "이 화면만 열어서는 AI가 클릭하지 않습니다. PC에서 로컬 봇 프로그램을 실행하세요."}</p>
  </section>;

  return <div className={`${role === "bot" ? "bot-mode" : "human-mode"} ${remoteMode ? "remote-mode" : "legacy-mode"} ${!session || state?.phase === "lobby" ? "match-lobby" : "match-live"}`}>
    <BrandHeader role={role} />
    <main className="arena-page">
      {remoteMode && <div className="lane-ribbon"><span className="lane-mark">{lane}</span><div><strong>{lane} 구역 · {role === "human" ? "인간 화면" : "AI 표시 화면"}</strong><span>{session ? `연결 코드 ${roomCode}` : "같은 구역끼리 연결하세요"}</span></div>{session && <span className={`connection-pill${connected ? " online" : ""}`}>{connected ? "대결 연결됨" : "연결 확인 중"}</span>}</div>}
      <div className="intro-row"><div className="intro-copy"><div className="eyebrow">Songnae High School · Alpha Club</div><h1>누가 더 빠르게 <em>알아볼까?</em></h1><p>당신의 직감과 AI의 눈. 같은 사진 위에서 만나는 한판 승부.</p></div><div className="round-chip"><span className="icon-box"><Sparkles size={18} /></span><div>HUMAN vs AI<small>사진으로 겨루는 관찰력 대결</small></div></div></div>
      <div className="arena-workspace">
        <div className="match-column">
          <div className="duel-banner"><div className="player"><span className="avatar"><UserRound size={22} strokeWidth={1.7} /></span><div><strong>HUMAN <span style={{ color: "#6ce6df", fontSize: 10, marginLeft: 4 }}>{role === "human" ? "YOU" : ""}</span></strong><small><span className="online" />{session ? playerStatus(state?.human) : "새로운 도전자를 기다려요"}</small></div></div><div className="vs-stamp">VS</div><div className="player bot"><div style={{ textAlign: "right" }}><strong>ALPHA AI</strong><small style={{ justifyContent: "flex-end" }}>{state?.bot.ready ? <span className="online" /> : null}{playerStatus(state?.bot, "bot")}</small></div><span className="avatar"><Bot size={23} strokeWidth={1.7} /></span></div></div>
          <section className="game-panel" aria-label="CAPTCHA 대결">
            <div className="question-row"><div id="public-question"><div className="question-kicker">CHALLENGE {String(state?.phase === "lobby" || queued ? (state?.roundNumber || 0) + 1 : state?.roundNumber || 1).padStart(2, "0")} <span style={{ color: "#9aa8a1", margin: "0 5px" }}>/</span> IMAGE CAPTCHA</div><h2>{waitingForStart ? "AI와 함께 출발할 준비 중" : roundView.topic?.prompt || "사진을 보고, 조건에 맞게 선택하세요"}</h2><p>{waitingForStart ? "준비가 끝나면 같은 순간에 출발합니다. 대기 시간은 경기 시간에 포함되지 않아요." : cancellationMessage || (viewer ? "PC의 AI가 고른 사진을 실시간으로 보여줍니다." : "해당하는 사진을 모두 선택한 뒤 정답을 제출하세요.")}</p></div><div className="timer" role="timer" aria-label={`진행 시간 ${timer}초`}><div className="timer-label"><Timer size={10} />진행 시간</div><div className="timer-value">{timer}<span style={{ fontSize: 10, marginLeft: 3, fontWeight: 500 }}>s</span></div></div></div>
            <div className="game-grid" id="captcha-grid" role="group" aria-label={waitingForStart ? "AI 출발 준비 대기" : "서로 다른 사진 9개"}>
              {Array.from({ length: 9 }, (_, index) => {
                const tile = tiles[index];
                const tileRound = state?.roundId;
                return tile && (started || !!state?.imageLoad) ? <button key={`${state?.roundId}:${tile.id}`} type="button" style={{ visibility: started ? "visible" : "hidden" }} aria-hidden={!started} className={`tile${visibleSelected.has(tile.id) ? " selected" : ""}`} aria-label={`사진 ${index + 1}${viewer ? " · AI 선택 표시" : ""}`} aria-pressed={visibleSelected.has(tile.id)} disabled={!canSelect} onClick={viewer ? undefined : () => setSelected(previous => { const next = new Set(previous); if (next.has(tile.id)) next.delete(tile.id); else next.add(tile.id); return next; })}>
                  {/* Opaque image URLs and generic alt text contain no answer labels. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={tile.url} alt={`문제 사진 ${index + 1}`} draggable={false} onLoad={async event => { const image = event.currentTarget; try { await image.decode(); if (!image.naturalWidth || !image.naturalHeight) throw new Error("empty image"); if (roundRef.current === tileRound) setLoaded(previous => new Set(previous).add(tile.id)); } catch { if (roundRef.current === tileRound) setImageError(true); } }} onError={() => { if (roundRef.current === tileRound) setImageError(true); }} /><span className="tile-check" aria-hidden="true"><Check size={14} strokeWidth={3} /></span>
                </button> : <div className="tile blank-tile" key={index} aria-hidden="true"><ImageIcon size={28} strokeWidth={1} /></div>;
              })}
              {!session ? <div className="grid-mask"><span className="mask-icon"><UsersRound size={26} strokeWidth={1.5} /></span><strong>새로운 대결이 기다려요</strong><p>{role === "human" ? "대결방을 만들고 AI와 함께 출발하세요." : "연결 코드를 입력해 대결에 입장하세요."}</p></div>
                : waitingForStart ? <div className="grid-mask" role="status"><LoaderCircle className="spinner" size={30} /><strong>{loadingImages ? "양쪽 화면의 사진을 준비 중" : "AI 출발 준비 중"}</strong><p>{loadingImages ? `인간 화면 ${state?.imageLoad?.humanReady ? "완료" : "준비 중"} · AI 화면 ${state?.imageLoad?.botReady ? "완료" : "준비 중"} · PC 봇 ${state?.imageLoad?.engineReady ? "완료" : "준비 중"}. 모두 준비되면 함께 출발합니다.` : "GPU 차례를 기다리고 있어요. 아직 문제와 사진은 공개되지 않고 타이머도 흐르지 않습니다."}</p>{role === "human" ? <button id="cancel-start" className="btn primary" disabled={!!busy || !connected} onClick={() => void act("cancel-start")}>{busy === "cancel-start" ? <LoaderCircle className="spinner" size={14} /> : <X size={14} />}출발 대기 취소</button> : <p>인간 화면에서 대기를 취소할 수 있습니다.</p>}</div>
                : imageError && state?.phase !== "result" ? <div className="grid-mask"><span className="mask-icon"><ImageIcon size={25} /></span><strong>사진을 불러오지 못했어요</strong><p>사진이 준비되어 있는지 관리자에게 확인해 주세요. 불완전한 문제는 제출할 수 없습니다.</p></div>
                : countdown ? <div className="grid-mask"><span className="eyebrow">모두 같은 순간에 출발!</span><strong className="countdown-number">{Math.max(1, Math.ceil(((state?.startAt || 0) - serverNow) / 1000))}</strong><p>{imagesReady ? "잠시 후 대결이 시작됩니다." : "문제 사진을 불러오고 있어요."}</p></div>
                : state?.phase === "lobby" ? <div className="grid-mask"><span className="mask-icon"><Link2 size={25} strokeWidth={1.5} /></span><strong>{remote ? canStart ? `${lane} 구역 출발 준비 완료` : needsEngineUpdate ? "PC 봇 업데이트 필요" : `${lane} 구역 연결 대기` : state.bot.ready ? "두 화면 연결 완료" : "상대와 연결하고 있어요"}</strong><p>{remote ? needsEngineUpdate ? "PC 봇 실행기를 최신 버전으로 업데이트하고 재시작해 주세요." : role === "human" ? "AI 표시 화면과 PC 봇을 연결한 뒤 시작하세요. 출발 준비가 끝나면 함께 시작합니다." : "인간 화면의 시작 요청 후 PC 봇의 출발 준비가 끝나면 함께 시작합니다." : role === "human" ? "PC 봇을 실행한 뒤 대결 시작 버튼을 눌러 주세요." : "PC 봇 프로그램을 실행하고 화면 준비를 알려 주세요."}</p>{role === "bot" && !remote && !state.bot.ready && <button className="btn primary" disabled={!!busy || !connected} onClick={() => void act("ready")}>{busy === "ready" ? <LoaderCircle className="spinner" size={15} /> : <Check size={15} />}봇 화면 준비</button>}</div>
                : state?.phase === "result" ? <div className="grid-mask"><span className="mask-icon"><Trophy size={27} strokeWidth={1.5} /></span><strong>{resultTitle}</strong><p>{winner === role ? "완벽한 정답을 먼저 제출해 승리했어요." : winner ? "상대가 먼저 완벽한 정답을 제출해 대결이 끝났어요." : "제한 시간 안에 완벽한 정답이 나오지 않았어요."}</p>{role === "human" ? <button id="next-participant" className="btn primary" disabled={!!busy || !!remote && !connected} onClick={() => void act(nextParticipantAction)}>{busy === nextParticipantAction ? <LoaderCircle className="spinner" size={14} /> : <UsersRound size={14} />}{nextParticipantLabel}</button> : remote ? <><strong style={{ fontSize: 16 }}>다음 참가자 대기 · 연결 유지</strong><p>인간 화면에서 다음 참가자를 준비하면 같은 방에서 다시 대기합니다.</p></> : <><p>새 참가자의 연결 코드로 다시 연결해 주세요.</p><button className="btn primary" disabled={!!busy} onClick={leave}><Link2 size={14} />새 코드로 연결하기</button></>}</div>
                : !imagesReady ? <div className="grid-mask"><LoaderCircle className="spinner" size={28} /><strong>{tiles.length === 9 ? "사진을 불러오고 있어요" : "문제 사진 준비 중"}</strong><p>{viewer ? "사진 9장을 불러온 뒤 AI의 선택을 보여줍니다." : "사진 9장이 모두 준비된 뒤 선택할 수 있어요."}</p></div>
                : deadlineReached ? <div className="grid-mask"><Clock3 size={28} /><strong>시간이 종료되었어요</strong><p>서버에서 대결 결과를 확인하고 있어요.</p></div> : null}
            </div>
            <div className="game-controls">{waitingForStart ? <span className="selection-count">출발 대기 · 진행 시간 0초</span> : <div className="selection-count"><CheckCheck size={15} /><span><strong>{visibleSelected.size}개</strong> {viewer ? "AI 선택" : "선택됨"}</span>{selected.size > 0 && role === "human" && <button className="btn text" style={{ fontSize: 10, paddingLeft: 5 }} disabled={!canSelect} onClick={() => setSelected(new Set())}>초기화</button>}</div>}{waitingForStart ? <span className="viewer-badge">{viewer ? "실시간 대기 표시" : "준비 후 자동 출발"}</span> : viewer ? <span className="viewer-badge"><Radio size={14} />실시간 표시 · 조작 없음</span> : <button id="captcha-submit" className="btn primary" disabled={!canSelect || !!busy} onClick={() => void act("submit")}>{busy === "submit" ? <LoaderCircle className="spinner" size={16} /> : <Check size={16} />}정답 제출<ArrowRight size={15} /></button>}</div>
            {feedback && state?.phase === "playing" && <p role="status" style={{ color: "#8e4735", fontSize: 12, margin: "12px 0 0" }}>{feedback}</p>}
            {viewer && remote && <div className={`engine-notice${remote.engineStage === "error" || state?.bot.correct === false ? " attention" : ""}`} role="status"><strong>{!connected ? "대결 연결을 확인하고 있어요" : state?.phase === "result" ? `다음 참가자 대기 · ${engineStatus(remote, state?.bot)}` : remote.engineStage === "submitted" && visibleSelected.size === 0 ? `AI 0개 선택 · ${engineStatus(remote, state?.bot)}` : engineStatus(remote, state?.bot)}</strong><span>{queued ? "출발 준비가 끝나면 이 대결의 인간과 AI가 함께 시작합니다. 대기 중에는 문제가 공개되지 않습니다." : state?.bot.correct === false && state?.phase !== "result" ? `${visibleSelected.size === 0 ? "AI가 조건에 맞는 사진을 고르지 않아 0개로 제출했습니다. " : "AI는 이 문제에 한 번 제출했습니다. "}인간은 시간이 끝나기 전까지 계속 풀 수 있습니다.` : remote.engineStage === "error" ? "PC 봇을 확인해 주세요. 이 화면에서 임의로 사진을 고르거나 제출하지 않습니다." : "AI의 선택만 표시합니다. 이 화면에서 답안을 바꿀 수 없습니다."}</span></div>}
          </section>
          <div className="game-footer"><span><LockKeyhole size={11} />두 플레이어에게 같은 문제, 같은 출발선</span><span>기본 제한 시간 90초 · 운영 가안</span></div>
        </div>
        <aside className="side-stack">
          {roomCard}
          <section className="side-card"><div className="eyebrow">Live match</div><h2 style={{ marginBottom: 18 }}>지금, 대결은</h2>{(["human", "bot"] as Role[]).map(playerRole => <div key={playerRole}><div className="live-score"><span className="score-person">{playerRole === "human" ? <UserRound size={15} /> : <Bot size={15} />}{playerRole === "human" ? "인간" : "알파 AI"}</span><span className="score-stat">{playerStatus(state?.[playerRole], playerRole)}</span></div><div className="progress-track"><div className="progress-fill" style={{ width: state?.[playerRole].correct === true ? "100%" : "0%" }} /></div></div>)}{state?.phase === "result" && <div className="result-box"><Trophy size={20} style={{ marginBottom: 6 }} /><div><strong>{resultTitle}</strong></div><p>첫 완벽 정답이 나오면 즉시 양쪽의 대결이 끝납니다.</p>{(["human", "bot"] as Role[]).map(playerRole => <div className="result-stat" key={playerRole}><span>{playerRole === "human" ? "인간" : "알파 AI"}</span><span>{winner === playerRole ? `승리 · ${(finalElapsed / 1000).toFixed(2)}초` : "종료 · 정답 미완료"}</span></div>)}</div>}</section>
          <section className="side-card rules-card" id="how-to-play"><div className="eyebrow">How to play</div><div className="rules-list"><div className="rule"><ImageIcon size={16} /><div><strong>사진을 자세히 살펴보세요</strong><p>9칸은 서로 다른 사진입니다. 조건에 맞는 사진을 모두 골라 주세요.</p></div></div><div className="rule"><ShieldCheck size={16} /><div><strong>정확하게, 그리고 빠르게</strong><p>첫 완벽 정답이 승리! 인간은 틀린 사진을 수정해 다시 제출할 수 있습니다. 시간은 계속 흐릅니다.</p></div></div><div className="rule"><Bot size={16} /><div><strong>AI는 PC에서 실행돼요</strong><p>{remoteMode ? "PC의 AI가 사진을 분석하고, 최소 0.25초 간격으로 선택을 표시한 뒤 한 번 제출합니다." : "PC의 로컬 봇이 사진을 분석하고 최소 0.25초 간격으로 타일을 클릭합니다."}</p></div></div></div></section>
        </aside>
      </div>
      {error && <div className="error-box" role="alert"><CircleHelp size={16} /><span>{error}</span><button aria-label="알림 닫기" onClick={() => setError("")}><X size={14} /></button></div>}
      <footer className="page-footer"><span><span className="footer-mark">ALPHA</span> &nbsp; 송내고등학교 알파 동아리</span><span>당신의 한 수, AI의 다음 수. <ChevronRight size={11} style={{ display: "inline" }} /></span></footer>
    </main>
    {role === "bot" && session && !remoteMode && <p className="status-note" style={{ maxWidth: 600, marginInline: "auto", padding: "0 20px 20px" }}>이 화면만 열어서는 AI가 클릭하지 않습니다. PC에서 로컬 봇 프로그램을 실행하세요.</p>}
    {role === "bot" && !session && !remoteMode && <div className="bot-lobby">{roomCard}</div>}
  </div>;
}




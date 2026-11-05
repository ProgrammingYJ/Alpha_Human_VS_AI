"""PC inference with lane-isolated remote selection events, never OS input.

This is the explicitly approved remote input mode. It uses public challenge
pixels prepared before common start and inferred only after it, never private
answers or filename-derived labels.
"""

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from io import BytesIO
import http.client
import json
import math
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import warnings

from PIL import Image

from .booth_bot import public_condition
from .tasks import select_tiles
from .timing import MIN_TILE_INTERVAL_SECONDS


USER_AGENT = "AlphaCaptchaRemoteEngine/1.0"
MAX_JSON_BYTES = 262144
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
PHOTO_PATH = re.compile(r"/api/photos/" + UUID, re.I)
ROOM_PATH = re.compile(r"/api/rooms/" + UUID + r"(?:/engine)?", re.I)
TERMINAL_PHASES = {"result", "expired"}
SAFE_ERROR_CODES = frozenset({
    "request_failed", "response_too_large", "connection_failed", "invalid_response", "invalid_public_image",
    "lane_mismatch", "unsupported_condition", "invalid_public_grid", "round_ended", "selection_not_acknowledged",
    "not_started", "cancelled", "heartbeat_failed", "wait_timeout", "round_changed", "engine_failed", "lane_busy",
    "engine_already_connected", "engine_not_ready", "engine_state_changed", "not_found", "room_expired",
    "round_in_progress", "selection_too_fast", "sequence_conflict", "selection_changed", "submission_changed",
    "invalid_action", "invalid_lane", "invalid_mode", "invalid_selection", "invalid_stage", "duplicate_selection",
    "forbidden", "unauthorized", "invalid_body", "invalid_code", "body_too_large", "bot_not_ready", "busy",
    "report_write_failed", "bank_not_ready", "storage_unavailable", "round_already_attempted", "lane_not_connected",
    "protocol_upgrade_required", "start_request_changed", "queue_expired", "room_changed", "invalid_start_request",
    "start_cancelled", "reservation_required", "plan_conflict", "plan_changed", "plan_active", "plan_too_late", "plan_not_acknowledged",
    "image_load_changed", "image_load_failed", "image_load_timeout", "images_timeout", "image_cache_changed",
    "not_loading",
})
_UNSET = object()


class RemoteEngineError(RuntimeError):
    """Only a bounded code/status, never server bodies or role credentials."""

    def __init__(self, code, *, status=None, retry_after=0.0):
        self.code = code if isinstance(code, str) and code in SAFE_ERROR_CODES else "request_failed"
        self.status = status
        self.retry_after = min(15.0, max(0.0, float(retry_after)))
        super().__init__(self.code)


def controlled_origin(value):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError("controlled booth origin required") from None
    if (parsed.scheme not in {"http", "https"} or parsed.hostname not in
            {"localhost", "127.0.0.1", "::1", "bot.marulee.dev"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        raise ValueError("controlled booth origin required")
    if parsed.hostname == "bot.marulee.dev" and (parsed.scheme != "https" or port not in {None, 443}):
        raise ValueError("public engine requires the controlled HTTPS origin")
    return f"{parsed.scheme}://{parsed.netloc}"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class KeepAliveOpener:
    """One origin-bound HTTP connection per calling thread; never redirects.

    urllib's standard handler sends Connection: close for every request. The
    engine polls persistently, so repeatedly paying TLS setup needlessly adds
    latency. Failed requests are not replayed here: EngineRoom alone decides
    which operations are safe to retry with identical bodies.
    """

    def __init__(self, origin):
        self.origin = origin
        self._local = threading.local()
        self._connections, self._lock = set(), threading.Lock()
        self.connections_created, self.requests_completed = 0, 0

    def open(self, request, timeout):
        if not request.full_url.startswith(self.origin + "/"):
            raise ValueError("origin-bound transport required")
        parsed = urlsplit(self.origin)
        connection = getattr(self._local, "connection", None)
        if connection is None:
            cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
            connection = cls(parsed.hostname, parsed.port, timeout=timeout)
            self._local.connection = connection
            with self._lock:
                self._connections.add(connection)
                self.connections_created += 1
        connection.timeout = timeout
        try:
            connection.request(request.get_method(), request.full_url[len(self.origin):],
                               body=request.data, headers=dict(request.header_items()))
            response = connection.getresponse()
            if response.status >= 300:
                # Do not leave an unread error response on a reusable socket.
                raw = response.read(8193)
                headers, status, reason = response.headers, response.status, response.reason
                response.close()
                connection.close()
                raise HTTPError(request.full_url, status, reason, headers, BytesIO(raw))
            with self._lock:
                self.requests_completed += 1
            return response
        except (OSError, http.client.HTTPException):
            connection.close()
            raise

    def close(self):
        with self._lock:
            connections, self._connections = self._connections, set()
        for connection in connections:
            connection.close()

    def discard_current(self):
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            with self._lock:
                self._connections.discard(connection)
            self._local.connection = None


class ControlledTransport:
    def __init__(self, origin, *, opener_factory=None, timeout=5.0):
        self.origin = controlled_origin(origin)
        self._keepalive = KeepAliveOpener(self.origin) if opener_factory is None else None
        self.opener_factory = opener_factory or (lambda: self._keepalive)
        self._image_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="alpha-rgb")
        self.timeout = timeout

    def close(self):
        self._image_pool.shutdown(wait=True, cancel_futures=True)
        if self._keepalive is not None:
            self._keepalive.close()

    def _read(self, path, *, token=None, body=None, image=False):
        if image:
            if not PHOTO_PATH.fullmatch(path) or body is not None or token is not None:
                raise ValueError("only public opaque challenge pixels may be downloaded")
        elif path != "/api/rooms/join" and not ROOM_PATH.fullmatch(path):
            raise ValueError("unsupported remote room endpoint")
        headers = {"User-Agent": USER_AGENT, "Accept": "image/jpeg,image/png,image/webp" if image else "application/json"}
        if token is not None:
            if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
                raise ValueError("invalid engine capability")
            headers["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, separators=(",", ":"), allow_nan=False).encode("utf-8")
        limit = MAX_IMAGE_BYTES if image else MAX_JSON_BYTES
        request = Request(self.origin + path, data=data, headers=headers)
        try:
            with self.opener_factory().open(request, timeout=self.timeout) as response:
                advertised = response.headers.get("Content-Length")
                if advertised and advertised.isdigit() and int(advertised) > limit:
                    raise RemoteEngineError("response_too_large")
                raw = response.read(limit + 1)
        except HTTPError as error:
            code = "request_failed"
            try:
                raw_error = error.read(8193)
                if len(raw_error) <= 8192:
                    value = json.loads(raw_error)
                    if isinstance(value, dict):
                        code = value.get("code", code)
            except (ValueError, OSError):
                pass
            try:
                retry = float(error.headers.get("Retry-After", "0"))
            except (TypeError, ValueError):
                retry = 0
            raise RemoteEngineError(code, status=error.code,
                                    retry_after=retry if math.isfinite(retry) else 0) from None
        except RemoteEngineError:
            if self._keepalive is not None:
                self._keepalive.discard_current()
            raise
        except (URLError, TimeoutError, OSError, http.client.HTTPException):
            raise RemoteEngineError("connection_failed") from None
        if len(raw) > limit:
            if self._keepalive is not None:
                self._keepalive.discard_current()
            raise RemoteEngineError("response_too_large")
        if image:
            return raw
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            raise RemoteEngineError("invalid_response") from None
        if not isinstance(value, dict):
            raise RemoteEngineError("invalid_response")
        return value

    def json(self, path, *, token=None, body=None):
        return self._read(path, token=token, body=body)

    def pixels(self, path):
        for attempt in range(2):
            try:
                raw = self._read(path, image=True)
                break
            except RemoteEngineError as error:
                if attempt or not EngineRoom._retryable(error):
                    raise
                time.sleep(max(0.2, error.retry_after))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(raw)) as image:
                    if image.format not in {"JPEG", "PNG", "WEBP"}:
                        raise ValueError("unsupported image format")
                    width, height = image.size
                    if min(width, height) < 3 or width * height > MAX_IMAGE_PIXELS:
                        raise ValueError("image dimensions exceed the bounded booth input")
                    image.load()
                    # Pixels only: source name, EXIF and server identity are not model inputs.
                    rgb = Image.new("RGB", image.size)
                    rgb.paste(image.convert("RGB"))
                    return rgb
        except (ValueError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise RemoteEngineError("invalid_public_image") from None


@dataclass(frozen=True)
class PublicSnapshot:
    phase: str
    round_id: str | None
    condition: dict | None
    photo_paths: tuple[str, ...]
    lane: str
    round_number: int
    start_request: dict | None
    start_at: int | None
    cancellation_reason: str | None
    gpu_reservation_supported: bool
    selection_plan_supported: bool
    bot_attempted: bool
    image_barrier_supported: bool
    image_load_id: str | None

    @classmethod
    def from_state(cls, value, expected_lane, *, allow_protocol_bootstrap=False):
        if not isinstance(value, dict):
            raise RemoteEngineError("invalid_response")
        remote = value.get("remote")
        if (not isinstance(remote, dict) or remote.get("mode") != "remote"
                or remote.get("lane") != expected_lane):
            raise RemoteEngineError("lane_mismatch")
        supported = remote.get("gpuReservationSupported")
        bootstrap = (allow_protocol_bootstrap and supported is False and value.get("phase") == "lobby"
                     and value.get("roundId") is None)
        if supported is not True and not bootstrap:
            raise RemoteEngineError("protocol_upgrade_required")
        phase = value.get("phase")
        if phase not in {"lobby", "queued", "loading", "countdown", "playing", "result", "expired"}:
            raise RemoteEngineError("invalid_response")
        image_supported = remote.get("imageBarrierSupported", False)
        if type(image_supported) is not bool:
            raise RemoteEngineError("invalid_response")
        if ("imageBarrierSupported" in remote and not image_supported
                and phase in {"lobby", "queued", "loading", "countdown"}
                and not (allow_protocol_bootstrap and phase == "lobby" and value.get("roundId") is None)):
            raise RemoteEngineError("protocol_upgrade_required")
        round_id = value.get("roundId")
        round_number = value.get("roundNumber")
        if type(round_number) is not int or round_number < 0:
            raise RemoteEngineError("invalid_response")
        if round_id is not None and (not isinstance(round_id, str) or not re.fullmatch(UUID, round_id, re.I)):
            raise RemoteEngineError("invalid_response")
        request = value.get("startRequest")
        if request is not None:
            if (not isinstance(request, dict) or set(request) != {"id", "requestedAt", "expiresAt"}
                    or not isinstance(request["id"], str) or not re.fullmatch(UUID, request["id"], re.I)
                    or type(request["requestedAt"]) is not int or type(request["expiresAt"]) is not int
                    or not 0 <= request["requestedAt"] < request["expiresAt"]):
                raise RemoteEngineError("invalid_start_request")
            request = dict(request)
        start_at = value.get("startAt")
        if start_at is not None and (type(start_at) is not int or start_at < 0):
            raise RemoteEngineError("invalid_response")
        reason = value.get("lastStartCancellationReason")
        if reason not in {None, "human_cancelled", "engine_disconnected", "engine_error", "queue_expired",
                          "image_load_failed", "image_load_timeout", "images_timeout"}:
            raise RemoteEngineError("invalid_response")
        if phase == "queued" and (request is None or round_id is not None or start_at is not None
                                  or value.get("topic") is not None or value.get("tiles") != []):
            raise RemoteEngineError("invalid_start_request")
        plan_supported = remote.get("selectionPlanSupported", False)
        bot = value.get("bot", {})
        bot_submitted = bot.get("submitted", False) if isinstance(bot, dict) else None
        if type(plan_supported) is not bool or type(bot_submitted) is not bool:
            raise RemoteEngineError("invalid_response")
        # A wrong submission keeps submitted_at null to preserve the human
        # retry contract. Its own public elapsed/correct fields still record
        # that the server performed the one fixed engine attempt.
        bot_attempted = bot_submitted or (type(bot.get("elapsedMs")) is int and bot["elapsedMs"] >= 0)
        condition = None
        paths = ()
        image_load_id = None
        if image_supported and phase in {"loading", "countdown", "playing"}:
            load = value.get("imageLoad")
            if (not isinstance(load, dict) or not isinstance(load.get("id"), str)
                    or not re.fullmatch(UUID, load["id"], re.I)
                    or type(load.get("expiresAt")) is not int or load["expiresAt"] < 0
                    or any(type(load.get(role + "Ready")) is not bool for role in ("human", "bot", "engine"))):
                raise RemoteEngineError("invalid_response")
            image_load_id = load["id"]
            if phase in {"countdown", "playing"} and not all(load[role + "Ready"] for role in ("human", "bot", "engine")):
                raise RemoteEngineError("invalid_response")
        if phase in {"loading", "countdown"} and image_supported:
            if (round_id is None or round_number < 1 or request is None or value.get("topic") is not None
                    or value.get("tiles") != [] or (phase == "loading" and
                    (start_at is not None or value.get("deadlineAt") is not None))):
                raise RemoteEngineError("invalid_start_request")
            tiles = value.get("preloadTiles")
        elif phase == "loading":
            raise RemoteEngineError("protocol_upgrade_required")
        if phase == "playing":
            if round_id is None or round_number < 1:
                raise RemoteEngineError("invalid_response")
            topic = value.get("topic")
            condition = topic.get("condition") if isinstance(topic, dict) else None
            try:
                public_condition(condition)
            except (ValueError, TypeError):
                raise RemoteEngineError("unsupported_condition") from None
            condition = dict(condition)
            tiles = value.get("tiles")
        if phase == "playing" or (image_supported and phase in {"loading", "countdown"}):
            if not isinstance(tiles, list) or len(tiles) != 9:
                raise RemoteEngineError("invalid_public_grid")
            paths = tuple(tile.get("url") if isinstance(tile, dict) else None for tile in tiles)
            if any(not isinstance(path, str) or not PHOTO_PATH.fullmatch(path) for path in paths) or len(set(paths)) != 9:
                raise RemoteEngineError("invalid_public_grid")
        # selectedIndices, answer-like fields, tile IDs, labels and original
        # filenames are deliberately absent from this model-facing projection.
        return cls(phase, round_id, condition, paths, expected_lane, round_number, request, start_at, reason, supported,
                   plan_supported, bot_attempted, image_supported, image_load_id)


class EngineRoom:
    def __init__(self, transport, lane, code, *, sleep=time.sleep):
        if lane not in {"A", "B"} or not isinstance(code, str) or not re.fullmatch(r"[A-Z2-9]{8}", code):
            raise ValueError("a lane and its eight-character pairing code are required")
        self.transport, self.lane, self.sleep = transport, lane, sleep
        joined = transport.json("/api/rooms/join", body={"role": "engine", "code": code, "lane": lane})
        room_id, token = joined.get("roomId"), joined.get("token")
        if (not isinstance(room_id, str) or not re.fullmatch(UUID, room_id, re.I)
                or not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token)):
            raise RemoteEngineError("invalid_response")
        initial = PublicSnapshot.from_state(joined.get("state"), lane, allow_protocol_bootstrap=True)
        # v11 predates the image-readiness field and accepts protocol 2 only.
        # A server advertising the field (even false before the first beat)
        # requires protocol 3; never bypass its readiness barrier.
        self._protocol_version = 3 if "imageBarrierSupported" in joined["state"]["remote"] else 2
        self._protocol_confirmed = (initial.gpu_reservation_supported and
                                    (initial.image_barrier_supported or "imageBarrierSupported" not in joined["state"]["remote"]))
        self._context_lock = threading.Lock()
        self._observed_context = (initial.round_id, initial.round_number, initial.start_request["id"] if initial.start_request else None)
        self._room_path, self._token = "/api/rooms/" + room_id, token

    def view(self):
        # GET is read-only. A bounded retry tolerates one transient dropped
        # connection without losing the lane or its in-memory capability.
        value = None
        for attempt in range(2):
            try:
                value = self.transport.json(self._room_path, token=self._token)
                break
            except RemoteEngineError as error:
                if attempt or not self._retryable(error):
                    raise
                self.sleep(max(0.2, error.retry_after))
        raw = value.get("state", value)
        # A live v11 connection can observe the protocol-3 deployment while
        # sitting in a lobby. Upgrade its next heartbeat before arming a new
        # start; never interpret an advertised false flag as an old server.
        with self._context_lock:
            if raw.get("phase") == "lobby" and "imageBarrierSupported" in raw.get("remote", {}) and self._protocol_version < 3:
                self._protocol_version, self._protocol_confirmed = 3, False
        snapshot = PublicSnapshot.from_state(raw, self.lane,
                                             allow_protocol_bootstrap=not self._protocol_confirmed)
        with self._context_lock:
            self._observed_context = (snapshot.round_id, snapshot.round_number, snapshot.start_request["id"] if snapshot.start_request else None)
        return snapshot

    @staticmethod
    def _retryable(error):
        return error.status == 429 or error.status in {502, 503, 504} or error.code == "connection_failed"

    def _action(self, body, *, retries=0):
        for attempt in range(retries + 1):
            try:
                return self.transport.json(self._room_path + "/engine", token=self._token, body=body)
            except RemoteEngineError as error:
                retryable = self._retryable(error)
                if not retryable or attempt >= retries:
                    raise
                # A selection retry sends the exact same sequence and tile.
                self.sleep(max(1.0, error.retry_after))
        raise AssertionError("unreachable")

    def heartbeat(self, stage, *, round_id=_UNSET, round_number=_UNSET, request_id=_UNSET):
        if stage not in {"ready", "waiting_gpu", "reserved", "loading_images", "images_ready",
                         "inferencing", "selecting", "submitted", "error"}:
            raise ValueError("invalid engine stage")
        if round_id is _UNSET or round_number is _UNSET:
            if round_id is not _UNSET or round_number is not _UNSET:
                raise ValueError("both heartbeat round fields are required together")
            with self._context_lock:
                round_id, round_number, observed_request = self._observed_context
                if request_id is _UNSET:
                    request_id = observed_request
        elif request_id is _UNSET:
            with self._context_lock:
                request_id = self._observed_context[2]
        if (round_id is not None and (not isinstance(round_id, str) or not re.fullmatch(UUID, round_id, re.I))
                or type(round_number) is not int or round_number < 0):
            raise ValueError("invalid heartbeat round context")
        if request_id is not None and (not isinstance(request_id, str) or not re.fullmatch(UUID, request_id, re.I)):
            raise ValueError("invalid heartbeat request identity")
        result = self._action({"action": "heartbeat", "stage": stage,
                               "protocolVersion": self._protocol_version, "requestId": request_id,
                               "roundId": round_id, "roundNumber": round_number}, retries=1)
        raw = result.get("state", {})
        if raw.get("phase") == "lobby" and "imageBarrierSupported" in raw.get("remote", {}) and self._protocol_version < 3:
            with self._context_lock:
                self._protocol_version, self._protocol_confirmed = 3, False
            # Deployment can arrive between the last GET and this heartbeat.
            # Upgrade this same lobby context once, preserving the capability.
            result = self._action({"action": "heartbeat", "stage": stage, "protocolVersion": 3,
                                   "requestId": request_id, "roundId": round_id, "roundNumber": round_number}, retries=1)
        current = PublicSnapshot.from_state(result.get("state"), self.lane)
        self._protocol_confirmed = True
        with self._context_lock:
            self._observed_context = (current.round_id, current.round_number,
                                      current.start_request["id"] if current.start_request else None)
        return result

    def begin(self, request_id, round_number):
        if (not isinstance(request_id, str) or not re.fullmatch(UUID, request_id, re.I)
                or type(round_number) is not int or round_number < 0):
            raise ValueError("invalid start reservation context")
        value = self._action({"action": "begin", "requestId": request_id,
                              "roundNumber": round_number}, retries=2)
        current = PublicSnapshot.from_state(value.get("state"), self.lane)
        if (current.phase not in {"loading", "countdown", "playing", "result"} or current.round_id is None
                or current.round_number != round_number + 1 or current.start_request is None
                or current.start_request["id"] != request_id):
            raise RemoteEngineError("start_request_changed")
        with self._context_lock:
            self._observed_context = (current.round_id, current.round_number, request_id)
        return current

    def images_ready(self, snapshot):
        """Acknowledge this epoch only after all nine public images decode."""
        if (not snapshot.image_barrier_supported or snapshot.phase not in {"loading", "countdown"}
                or snapshot.image_load_id is None or snapshot.start_request is None):
            raise RemoteEngineError("invalid_start_request")
        try:
            value = self._action({"action": "images_ready", "roundId": snapshot.round_id,
                                  "roundNumber": snapshot.round_number, "requestId": snapshot.start_request["id"],
                                  "imageLoadId": snapshot.image_load_id}, retries=2)
            current = PublicSnapshot.from_state(value.get("state"), self.lane)
        except RemoteEngineError as error:
            if error.code != "not_loading" and not self._retryable(error):
                raise
            # The ready write can succeed while its ACK is lost. A retry
            # after the common start is legitimately "not_loading". Only a
            # fresh server state proving all three flags and this exact epoch
            # may recover that ambiguous write; it never starts inference early.
            current = self.view()
            if current.phase in TERMINAL_PHASES:
                raise RemoteEngineError("round_ended") from None
            if current.phase != "playing":
                raise error
        if (current.round_id != snapshot.round_id or current.round_number != snapshot.round_number
                or current.start_request is None or current.start_request["id"] != snapshot.start_request["id"]):
            raise RemoteEngineError("start_cancelled")
        if current.image_load_id != snapshot.image_load_id:
            raise RemoteEngineError("image_load_changed")
        with self._context_lock:
            self._observed_context = (current.round_id, current.round_number, current.start_request["id"])
        return current

    def select(self, round_id, sequence, tile_index):
        if (not isinstance(round_id, str) or not re.fullmatch(UUID, round_id, re.I)
                or type(sequence) is not int or not 1 <= sequence <= 9
                or type(tile_index) is not int or not 0 <= tile_index <= 8):
            raise ValueError("invalid deterministic selection event")
        result = self._action({"action": "select", "roundId": round_id,
                               "sequence": sequence, "tileIndex": tile_index}, retries=2)
        state = result.get("state")
        snapshot = PublicSnapshot.from_state(state, self.lane)
        if snapshot.phase != "playing" or snapshot.round_id != round_id:
            raise RemoteEngineError("round_ended")
        remote = state.get("remote", {})
        if remote.get("sequence") != sequence or tile_index not in remote.get("selectedIndices", []):
            raise RemoteEngineError("selection_not_acknowledged")
        return result

    def submit(self, round_id):
        if not isinstance(round_id, str) or not re.fullmatch(UUID, round_id, re.I):
            raise ValueError("invalid round identity")
        # A lost submit response must never initiate another model attempt.
        return self._action({"action": "submit", "roundId": round_id})

    def plan(self, round_id, selected_indices):
        """Upload one immutable model decision; the server owns playback time.

        An identical retry receives the original schedule, even if playback
        has finished. The ACK is not evidence of actual per-tile dispatch.
        """
        if (not isinstance(round_id, str) or not re.fullmatch(UUID, round_id, re.I)
                or not isinstance(selected_indices, list) or len(selected_indices) > 9
                or any(type(index) is not int or not 0 <= index <= 8 for index in selected_indices)
                or len(set(selected_indices)) != len(selected_indices)):
            raise ValueError("invalid deterministic selection plan")
        value = self._action({"action": "plan", "roundId": round_id,
                              "selectedIndices": list(selected_indices)}, retries=2)
        plan, server_now = value.get("plan"), value.get("serverNow")
        if (not isinstance(plan, dict) or plan.get("roundId") != round_id
                or not isinstance(plan.get("selectedIndices"), list)
                or any(type(index) is not int for index in plan["selectedIndices"])
                or plan.get("selectedIndices") != selected_indices
                or type(plan.get("intervalMs")) is not int or plan["intervalMs"] != 250
                or type(plan.get("startAt")) is not int or not 0 <= plan["startAt"] <= 2 ** 53 - 1
                or type(plan.get("submitAt")) is not int
                or not 0 <= plan["submitAt"] <= 2 ** 53 - 1
                or plan["submitAt"] != plan["startAt"] + max(0, len(selected_indices) - 1) * 250
                or type(server_now) is not int or not 0 <= server_now <= 2 ** 53 - 1):
            raise RemoteEngineError("plan_not_acknowledged")
        # Exclude room identity, capabilities and any future response fields.
        return {"startAt": plan["startAt"], "intervalMs": 250, "submitAt": plan["submitAt"],
                "selectedIndices": list(selected_indices), "serverNow": server_now}

    def pixels(self, snapshot):
        if (snapshot.phase != "playing" and not (snapshot.image_barrier_supported and snapshot.phase == "loading")) or len(snapshot.photo_paths) != 9:
            raise RemoteEngineError("not_started")
        # Independent public RGB downloads may overlap without sharing an
        # opener or credential. map preserves the original nine-tile order;
        # leaving the context joins all started work on success or failure.
        pool = getattr(self.transport, "_image_pool", None)
        owned_pool = pool is None
        pool = pool or ThreadPoolExecutor(max_workers=3, thread_name_prefix="alpha-rgb")
        try:
            futures = [pool.submit(self.transport.pixels, path) for path in snapshot.photo_paths]
            try:
                return [future.result() for future in futures]
            except Exception:
                # Join pending downloads before clearing successful decodes;
                # no stale round pixels survive a partially failed preload.
                for future in futures:
                    try:
                        future.result().close()
                    except Exception:
                        pass
                raise
        finally:
            if owned_pool:
                pool.shutdown(wait=True)


class GpuReservation:
    def __init__(self, pool, acquired_at, wait_seconds, *, context_check_seconds=0.0, wall_wait_seconds=None,
                 worker_index=0):
        self.pool, self.acquired_at, self.wait_seconds = pool, acquired_at, wait_seconds
        self.context_check_seconds = context_check_seconds
        self.wall_wait_seconds = wait_seconds if wall_wait_seconds is None else wall_wait_seconds
        self.worker_index = worker_index
        self.thread_id, self.released = threading.get_ident(), False

    def validate(self, pool):
        if self.pool is not pool or self.released or self.thread_id != threading.get_ident():
            raise RemoteEngineError("reservation_required")

    def release(self):
        self.pool.release(self)


class FifoGpuReservations:
    """FIFO in this engine's observed registration order, with cancellable waits."""

    def __init__(self, lock):
        self.lock, self.condition, self.pending, self.busy = lock, threading.Condition(), [], False
        self.capacity = 1

    def release(self, claim):
        with self.condition:
            if not claim.released:
                claim.released = True
                self.lock.release()
                self.busy = False
                self.condition.notify_all()

    def acquire(self, *, active=lambda: True, clock=time.monotonic):
        ticket, queued_at, native_acquired, context_seconds = object(), clock(), False, 0.0
        with self.condition:
            self.pending.append(ticket)
        try:
            while True:
                # Network context checks are outside the queue mutex; a slow
                # server response never blocks the other lane's release.
                check_started = clock()
                valid = active()
                context_seconds += clock() - check_started
                if not valid:
                    raise RemoteEngineError("start_cancelled")
                with self.condition:
                    if self.pending[0] is ticket and not self.busy and self.lock.acquire(blocking=False):
                        native_acquired = True
                        acquired_at = clock()  # Exact acquisition, before any active() HTTP.
                        self.pending.pop(0)
                        self.busy = True
                        wall_wait = acquired_at - queued_at
                        return GpuReservation(self, acquired_at, wall_wait,
                                              context_check_seconds=context_seconds, wall_wait_seconds=wall_wait)
                    self.condition.wait(timeout=0.1)
        finally:
            if not native_acquired:
                with self.condition:
                    if ticket in self.pending:
                        self.pending.remove(ticket)
                    self.condition.notify_all()


class ParallelGpuReservations:
    """Two independent prestart/inference slots, without a lane-wide FIFO gate."""

    def __init__(self, capacity=2):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("worker capacity must be a positive integer")
        self.capacity = capacity
        self.condition, self.pending = threading.Condition(), []
        self._free_workers, self._claims = list(range(capacity)), {}

    @property
    def busy(self):
        with self.condition:
            return bool(self._claims)

    def acquire(self, *, active=lambda: True, clock=time.monotonic):
        ticket, queued_at, acquired, context_seconds = object(), clock(), False, 0.0
        with self.condition:
            self.pending.append(ticket)
        try:
            while True:
                check_started = clock()
                valid = active()
                context_seconds += clock() - check_started
                if not valid:
                    raise RemoteEngineError("start_cancelled")
                with self.condition:
                    # A slow context HTTP check in the other lane must not
                    # hold up a free slot, its image preparation or countdown.
                    if self._free_workers:
                        worker_index = self._free_workers.pop(0)
                        acquired_at = clock()
                        self.pending.remove(ticket)
                        wall_wait = acquired_at - queued_at
                        claim = GpuReservation(self, acquired_at, wall_wait, worker_index=worker_index,
                                               context_check_seconds=context_seconds,
                                               wall_wait_seconds=wall_wait)
                        self._claims[worker_index] = claim
                        acquired = True
                        return claim
                    self.condition.wait(timeout=0.1)
        finally:
            if not acquired:
                with self.condition:
                    if ticket in self.pending:
                        self.pending.remove(ticket)
                    self.condition.notify_all()

    def release(self, claim):
        with self.condition:
            if claim.released:
                return
            if self._claims.get(claim.worker_index) is not claim:
                raise RemoteEngineError("reservation_required")
            del self._claims[claim.worker_index]
            claim.released = True
            self._free_workers.append(claim.worker_index)
            self._free_workers.sort()
            self.condition.notify_all()


@dataclass
class InferenceWorker:
    predictor: object
    tree_predictor: object
    stream: object = None


class SharedModels:
    """Frozen weights loaded once, with isolated concurrent inference workers.

    Parallel is the operator default. Each reservation owns one worker through
    image readiness, countdown and inference, so neither lane waits for the
    other's prestart path. CUDA workers have distinct streams; this requests
    concurrent execution, not a fixed GPU percentage or a latency guarantee.
    """

    def __init__(self, predictor, tree_predictor, *, lock=None, execution_mode="parallel"):
        if execution_mode not in {"parallel", "serial"}:
            raise ValueError("inference mode must be parallel or serial")
        self.predictor, self.tree_predictor = predictor, tree_predictor
        self.execution_mode = execution_mode
        self.lock = lock or threading.Lock()
        self.reservations = (ParallelGpuReservations() if execution_mode == "parallel"
                             else FifoGpuReservations(self.lock))
        self._torch, self._cuda_device = None, None
        devices = {str(device) for model in (predictor, tree_predictor)
                   if (device := getattr(model, "device", None)) is not None}
        cuda_devices = {device for device in devices if device.startswith("cuda")}
        if cuda_devices:
            if len(cuda_devices) != 1 or len(devices) != 1:
                raise ValueError("all shared models must use the same CUDA device")
            self._cuda_device = next(iter(cuda_devices))
        if devices:
            import torch
            self._torch = torch
        self.workers = []
        for _ in range(self.reservations.capacity):
            # The real predictors expose this fork to keep processor/tokenizer
            # and diagnostic state private while referencing the same weights.
            # Lightweight injected test predictors need no ML dependency.
            predictor_fork = getattr(predictor, "fork_for_inference", None)
            tree_fork = getattr(tree_predictor, "fork_for_inference", None)
            worker = InferenceWorker(
                predictor_fork() if predictor_fork is not None else predictor,
                tree_fork() if tree_fork is not None else tree_predictor)
            if self._cuda_device is not None:
                torch = self._torch
                with torch.cuda.device(self._cuda_device):
                    worker.stream = torch.cuda.Stream(device=self._cuda_device)
                    worker.stream.wait_stream(torch.cuda.current_stream(self._cuda_device))
            self.workers.append(worker)

    def execution_metadata(self):
        return {"inference_mode": self.execution_mode,
                "max_concurrent_inferences": self.reservations.capacity,
                "cuda_stream_count": sum(worker.stream is not None for worker in self.workers),
                "model_weights_shared": True,
                "gpu_percentage_partitioned": False}

    @contextmanager
    def _worker_execution(self, worker):
        if self._torch is None:
            yield
            return
        with self._torch.inference_mode():
            if worker.stream is None:
                yield
            else:
                with self._torch.cuda.device(self._cuda_device), self._torch.cuda.stream(worker.stream):
                    try:
                        yield
                    finally:
                        # Complete this stream, not all CUDA work from both
                        # lanes, before publishing results/reusing its buffers.
                        worker.stream.synchronize()

    def reserve(self, *, active=lambda: True, clock=time.monotonic):
        return self.reservations.acquire(active=active, clock=clock)

    def warm_up(self, *, clock=time.monotonic):
        """Initialize kernels on synthetic pixels before accepting any room.

        No challenge, answer, model update or threshold adjustment is involved.
        The three deployed models and their fixed preprocessing are unchanged.
        """
        started = clock()
        images = [Image.new("RGB", (192, 192), (127, 127, 127)) for _ in range(9)]
        claims = []
        try:
            # Hold each slot once so both streams/processors are initialized;
            # sequential acquisitions otherwise repeatedly choose worker zero.
            for _ in self.workers:
                claims.append(self.reserve())
            for claim in claims:
                self.infer(images, {"task_type": "building_present"}, reservation=claim)
                self.infer(images, {"task_type": "person_count", "operator": "gte", "n": 3}, reservation=claim)
                self.infer(images, {"task_type": "tree_count", "operator": "gte", "n": 3}, reservation=claim)
        finally:
            for claim in claims:
                claim.release()
            for image in images:
                image.close()
        return {"seconds": clock() - started, "synthetic_rgb_only": True,
                "model_families": ["presence", "person", "tree"], "challenge_images_used": 0,
                "workers_warmed": len(self.workers), **self.execution_metadata()}

    def infer(self, images, condition, *, active=lambda: True, timings=None, clock=time.monotonic,
              reservation=None):
        if len(images) != 9 or any(not isinstance(image, Image.Image) or image.mode != "RGB" for image in images):
            raise ValueError("exactly nine RGB pixels-only images are required")
        parsed = public_condition(condition)
        owned = reservation is None
        try:
            claim = reservation or self.reserve(active=active, clock=clock)
        except RemoteEngineError as error:
            if error.code == "start_cancelled":
                raise RemoteEngineError("round_ended") from None
            raise
        claim.validate(self.reservations)
        worker = self.workers[claim.worker_index]
        try:
            if not active():
                raise RemoteEngineError("round_ended")
            inference_started = clock()
            if timings is not None:
                timings["gpu_queue_seconds"] = claim.wait_seconds if owned else 0.0
                timings["timing_schema_version"] = 2
                timings.update(self.execution_metadata(), inference_worker_index=claim.worker_index)
            with self._worker_execution(worker):
                if isinstance(parsed, dict):
                    decisions = worker.tree_predictor.predict_at_least_three(images)
                else:
                    targeted = getattr(worker.predictor, "predict_condition_tiles", None)
                    rows = targeted(images, parsed) if targeted is not None else worker.predictor.predict_tiles(images)
            model_returned = clock()
            if isinstance(parsed, dict):
                if len(decisions) != 9 or any(type(value) is not bool for value in decisions):
                    raise ValueError("tree model returned invalid decisions")
                selected = [index for index, value in enumerate(decisions) if value]
                predictions = [{"at_least_three": value} for value in decisions]
            else:
                threshold = worker.predictor.presence_metadata["profile"]["threshold"]
                selected = select_tiles(rows, parsed, {name: threshold for name in ("tree", "building", "pond")})
                predictions = [{"presence_scores": dict(row.presence_scores), "person_count": row.person_count}
                               for row in rows]
            if timings is not None:
                timings["inference_seconds"] = model_returned - inference_started
                timings["model_inference_seconds"] = model_returned - inference_started
                timings["model_call_started_monotonic_seconds"] = inference_started
                timings["model_call_returned_monotonic_seconds"] = model_returned
        finally:
            if owned:
                claim.release()
        # For a pre-start reservation the caller releases immediately on
        # return and performs its HTTP guard afterwards. Legacy standalone
        # callers retain a post-inference guard after releasing the GPU.
        if owned and not active():
            raise RemoteEngineError("round_ended")
        return selected, predictions


class HeartbeatPump:
    def __init__(self, room, *, interval=3.0):
        self.room, self.interval = room, interval
        self.stage = "ready"
        self.round_id, self.round_number = None, 0
        self.request_id = None
        self.stopped = threading.Event()
        self.failed = threading.Event()
        self.failure_code = None
        self._stage_lock, self._send_lock = threading.Lock(), threading.Lock()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def beat(self):
        with self._send_lock:
            with self._stage_lock:
                stage, round_id, round_number, request_id = self.stage, self.round_id, self.round_number, self.request_id
            try:
                self.room.heartbeat(stage, round_id=round_id, round_number=round_number, request_id=request_id)
            except RemoteEngineError as error:
                if error.code not in {"round_changed", "round_ended", "round_in_progress", "engine_state_changed", "start_request_changed"}:
                    raise
                # A transition may invalidate a heartbeat while inference is
                # still running. Rebind only to a newly read public context;
                # never replay an old lobby ready into the next participant.
                snapshot = self.room.view()
                with self._stage_lock:
                    request_id = snapshot.start_request["id"] if snapshot.start_request else None
                    context_changed = (self.round_id, self.round_number, self.request_id) != (snapshot.round_id, snapshot.round_number, request_id)
                    self.round_id, self.round_number = snapshot.round_id, snapshot.round_number
                    self.request_id = request_id
                    if self.stage == "error":
                        # An abort racing /next must not arm the new lobby
                        # just before this worker exits.
                        pass
                    elif snapshot.phase == "lobby":
                        self.stage = "ready"
                    elif snapshot.phase == "queued":
                        self.stage = "waiting_gpu"
                    elif snapshot.phase == "loading":
                        self.stage = "loading_images"
                    elif snapshot.phase == "countdown" and snapshot.image_barrier_supported:
                        self.stage = "images_ready"
                    elif snapshot.phase in TERMINAL_PHASES:
                        self.stage = "submitted"
                    elif context_changed or self.stage == "ready":
                        self.stage = "inferencing"
                    stage, round_id, round_number, request_id = self.stage, self.round_id, self.round_number, self.request_id
                try:
                    self.room.heartbeat(stage, round_id=round_id, round_number=round_number, request_id=request_id)
                except RemoteEngineError as retry_error:
                    if retry_error.code not in {"round_changed", "round_ended", "round_in_progress", "engine_state_changed", "start_request_changed"}:
                        raise
                    # Two immediate transitions are not a permanent connection
                    # failure; the next poll/heartbeat will bind again.

    def start(self):
        self.beat()
        self.thread.start()

    def set_stage(self, stage, *, snapshot=None):
        with self._stage_lock:
            self.stage = stage
            if snapshot is not None:
                self.round_id, self.round_number = snapshot.round_id, snapshot.round_number
                self.request_id = snapshot.start_request["id"] if snapshot.start_request else None
        self.beat()

    def defer_stage(self, stage, *, snapshot=None):
        """Update progress without adding a synchronous HTTP trip to play.

        The existing periodic heartbeat still sends this stage. Queue/begin
        and image acknowledgements keep their immediate, server-bound checks.
        """
        with self._stage_lock:
            self.stage = stage
            if snapshot is not None:
                self.round_id, self.round_number = snapshot.round_id, snapshot.round_number
                self.request_id = snapshot.start_request["id"] if snapshot.start_request else None

    def bind(self, snapshot):
        with self._stage_lock:
            self.round_id, self.round_number = snapshot.round_id, snapshot.round_number
            self.request_id = snapshot.start_request["id"] if snapshot.start_request else None
            self.stage = ("ready" if snapshot.phase == "lobby" else "waiting_gpu" if snapshot.phase == "queued"
                          else "loading_images" if snapshot.phase == "loading"
                          else "images_ready" if snapshot.phase == "countdown" and snapshot.image_barrier_supported
                          else "submitted" if snapshot.phase in TERMINAL_PHASES else "inferencing")

    def _loop(self):
        while not self.stopped.wait(self.interval):
            try:
                self.beat()
            except Exception as error:
                self.failure_code = error.code if isinstance(error, RemoteEngineError) else "heartbeat_failed"
                self.failed.set()
                return

    def close(self):
        self.stopped.set()
        if self.thread.is_alive():
            self.thread.join(timeout=6)


def run_one_room(room, models, *, cancel=None, clock=time.monotonic, sleep=time.sleep,
                 wait_seconds=1800.0, heartbeat_factory=HeartbeatPump, progress=lambda _: None,
                 pump=None, starting_snapshot=None, attempted_rounds=None, attempted_requests=None):
    cancel = cancel or threading.Event()
    owned_pump = pump is None
    pump = pump or heartbeat_factory(room)
    started, report = clock(), {"mode": "remote", "lane": room.lane, "source": "actual_model_public_rgb_pixels",
        "model_predictions_per_game": 0, "selected_indices": [], "selection_events": [],
        "submit_sent": False, "logical_submission_count": 0, "logical_submit_scheduled": False,
        "selection_transport": "per_tile_http", "planned_selection_events": [],
        "server_submission_observed": False, "minimum_tile_interval_seconds": MIN_TILE_INTERVAL_SECONDS,
        "screen_capture_performed": False, "os_mouse_control_performed": False,
        "role_token_or_pairing_code_logged": False, "new_accuracy_measurement": False,
        "image_barrier_used": False, "prestart_image_download_seconds": 0.0,
        "public_image_download_during_game_seconds": 0.0, "image_cache_reused": False,
        "image_ready_ack_count": 0, "prestart_inference_count": 0}
    if isinstance(models, SharedModels):
        report.update(models.execution_metadata())
    reservation, state_http_seconds = None, 0.0
    images, image_cache_key, acknowledged_epoch, barrier_context = None, None, None, None
    def view():
        nonlocal state_http_seconds
        sent = clock()
        try:
            return room.view()
        finally:
            state_http_seconds += clock() - sent
    def ensure_running():
        if cancel.is_set():
            raise RemoteEngineError("cancelled")
        if pump.failed.is_set():
            raise RemoteEngineError("round_ended" if getattr(pump, "failure_code", None) == "round_ended" else "heartbeat_failed")
        if clock() - started >= wait_seconds:
            raise RemoteEngineError("wait_timeout")
    def sleep_checked(seconds):
        end = clock() + seconds
        while clock() < end:
            ensure_running()
            sleep(min(0.1, end - clock()))
    def playback_stage(stage, current):
        # Preparing/begin acknowledgements remain synchronous. Once images
        # are ready, progress updates need not delay the actual model/plan.
        if current.image_barrier_supported and current.selection_plan_supported and isinstance(pump, HeartbeatPump):
            pump.defer_stage(stage, snapshot=current)
        else:
            pump.set_stage(stage, snapshot=current)
    try:
        if owned_pump:
            if isinstance(pump, HeartbeatPump):
                pump.bind(view())
            pump.start()
            progress("ready")
        while True:
            ensure_running()
            snapshot = starting_snapshot or view()
            starting_snapshot = None
            if snapshot.phase in TERMINAL_PHASES:
                report["status"] = "ended_before_inference"
                return report
            if snapshot.phase == "queued":
                ticket, prior_number = snapshot.start_request["id"], snapshot.round_number
                if attempted_requests is not None:
                    if ticket in attempted_requests:
                        raise RemoteEngineError("start_request_changed")
                    attempted_requests.add(ticket)
                observed_at, queue_http_started = clock(), state_http_seconds
                pump.set_stage("waiting_gpu", snapshot=snapshot)
                progress("waiting_gpu")
                def queue_active():
                    ensure_running()
                    current = view()
                    return (current.phase == "queued" and current.round_number == prior_number
                            and current.start_request is not None and current.start_request["id"] == ticket)
                reservation = models.reserve(active=queue_active, clock=clock)
                report.update(gpu_reserved_before_start=True,
                              inference_worker_index=reservation.worker_index,
                              gpu_reserved_monotonic_seconds=reservation.acquired_at,
                              prestart_gpu_queue_seconds=reservation.wait_seconds,
                              prestart_queue_wall_seconds=reservation.wall_wait_seconds,
                              prestart_queue_context_check_seconds=reservation.context_check_seconds,
                              prestart_queue_state_http_seconds=state_http_seconds - queue_http_started)
                report["timing_note"] = ("schema2: prestart queue is registration-to-acquisition wall time including context checks; "
                                         "model call includes fixed preprocessing/postprocessing but excludes status HTTP; "
                                         "v8 timing values are not directly comparable")
                if not queue_active():
                    raise RemoteEngineError("start_cancelled")
                pump.set_stage("reserved", snapshot=snapshot)
                progress("reserved")
                begin_sent = clock()
                report["begin_sent_monotonic_seconds"] = begin_sent
                snapshot = room.begin(ticket, prior_number)
                report.update(begin_request_seconds=clock() - begin_sent,
                              begin_ack_monotonic_seconds=clock(),
                              request_observed_to_begin_ack_seconds=clock() - observed_at)
                if snapshot.start_at is not None:
                    report["server_request_to_common_start_seconds"] = (snapshot.start_at - snapshot.start_request["requestedAt"]) / 1000
                if snapshot.image_barrier_supported:
                    barrier_context = (snapshot.round_id, snapshot.round_number, ticket)
                    report["image_barrier_used"] = True
                else:
                    pump.set_stage("inferencing", snapshot=snapshot)
            if barrier_context is not None:
                current_context = (snapshot.round_id, snapshot.round_number,
                                   snapshot.start_request["id"] if snapshot.start_request else None)
                if current_context != barrier_context:
                    raise RemoteEngineError("start_cancelled")
                if not snapshot.image_barrier_supported:
                    raise RemoteEngineError("protocol_upgrade_required")
            if snapshot.phase in {"loading", "countdown"} and snapshot.image_barrier_supported:
                if reservation is None or barrier_context is None:
                    raise RemoteEngineError("reservation_required")
                key = (snapshot.round_id, snapshot.photo_paths)
                if images is None:
                    if snapshot.phase != "loading":
                        raise RemoteEngineError("image_cache_changed")
                    pump.set_stage("loading_images", snapshot=snapshot)
                    progress("loading_images")
                    download_started = clock()
                    images = room.pixels(snapshot)
                    image_cache_key = key
                    report.update(prestart_image_download_seconds=clock() - download_started,
                                  public_image_download_seconds=clock() - download_started,
                                  image_download_completed_monotonic_seconds=clock())
                    ensure_running()
                elif key != image_cache_key:
                    raise RemoteEngineError("image_cache_changed")
                if acknowledged_epoch != snapshot.image_load_id:
                    ready_sent = clock()
                    try:
                        ready_state = room.images_ready(snapshot)
                    except RemoteEngineError as error:
                        if error.code != "image_load_changed":
                            raise
                        # A newly loaded browser resets the shared epoch. Keep
                        # the same pixels and acknowledge its next fresh state.
                        snapshot = view()
                        starting_snapshot = snapshot
                        continue
                    acknowledged_epoch = snapshot.image_load_id
                    report["image_ready_ack_count"] += 1
                    report["prestart_image_ready_ack_seconds"] = clock() - ready_sent
                    report["image_ready_ack_monotonic_seconds"] = clock()
                    snapshot = ready_state
                    pump.set_stage("images_ready", snapshot=snapshot)
                    progress("images_ready")
                if snapshot.start_at is not None:
                    report["server_request_to_common_start_seconds"] = (snapshot.start_at - snapshot.start_request["requestedAt"]) / 1000
            if snapshot.phase == "playing":
                if snapshot.start_request is not None and reservation is None:
                    raise RemoteEngineError("reservation_required")
                if snapshot.image_barrier_supported:
                    if (barrier_context is None or images is None or image_cache_key != (snapshot.round_id, snapshot.photo_paths)
                            or acknowledged_epoch != snapshot.image_load_id):
                        raise RemoteEngineError("image_cache_changed")
                    report.update(image_cache_reused=True, playing_observed_monotonic_seconds=clock())
                break
            if snapshot.phase == "countdown" and pump.stage == "ready":
                pump.set_stage("inferencing", snapshot=snapshot)
            sleep_checked(0.25)
        expected_round, expected_condition = snapshot.round_id, dict(snapshot.condition)
        expected_number = snapshot.round_number
        if attempted_rounds is not None:
            if expected_round in attempted_rounds:
                raise RemoteEngineError("round_already_attempted")
            attempted_rounds.add(expected_round)
        def active():
            ensure_running()
            now = view()
            return (now.phase == "playing" and now.round_id == expected_round
                    and now.round_number == expected_number and now.condition == expected_condition)
        playback_stage("inferencing", snapshot)
        progress("inferencing")
        # SharedModels performs its own authoritative pre-model guard. Keep
        # this separate guard for the older standalone/test model adapters.
        if (not isinstance(models, SharedModels) or not snapshot.image_barrier_supported) and not active():
            raise RemoteEngineError("round_ended")
        if images is None:
            # Compatibility for an already active pre-barrier round only.
            download_started = clock()
            images = room.pixels(snapshot)
            report["public_image_download_seconds"] = clock() - download_started
            report["public_image_download_during_game_seconds"] = clock() - download_started
        inference_started = clock()
        timings = {}
        try:
            if reservation is None:
                selected, predictions = models.infer(images, expected_condition, active=active, timings=timings, clock=clock)
            else:
                selected, predictions = models.infer(images, expected_condition, active=active, timings=timings,
                                                     clock=clock, reservation=reservation)
        finally:
            if reservation is not None:
                released_at = clock()
                reservation.release()
                report.update(gpu_reservation_held_seconds=released_at - reservation.acquired_at,
                              gpu_released_monotonic_seconds=released_at,
                              gpu_reservation_released_seconds=released_at - started)
                reservation = None
        report.update(model_predictions_per_game=1, selected_indices=list(selected), predictions=predictions,
                      condition=expected_condition, inference_dispatch_seconds=clock() - inference_started,
                      **timings)
        if len(set(selected)) != len(selected) or any(type(index) is not int or not 0 <= index <= 8 for index in selected):
            raise ValueError("model selected invalid deterministic indices")
        playback_stage("selecting", snapshot)
        progress("selecting")
        if snapshot.selection_plan_supported:
            report.update(selection_transport="scheduled_plan", selection_timing_schema_version=3,
                          plan_upload_sent_seconds=clock() - started)
            schedule = room.plan(expected_round, list(selected))
            report.update(plan_upload_ack_seconds=clock() - started, logical_submit_scheduled=True,
                          logical_submission_count=1, plan_start_at_ms=schedule["startAt"],
                          planned_submit_at_ms=schedule["submitAt"],
                          plan_interval_ms=schedule["intervalMs"], plan_ack_server_now_ms=schedule["serverNow"],
                          selection_timing_note="Server schedule only; no per-tile HTTP or actual dispatch timestamps are recorded.")
            report["planned_selection_events"] = [
                {"sequence": sequence, "tile_index": tile_index,
                 "server_scheduled_at_ms": schedule["startAt"] + (sequence - 1) * schedule["intervalMs"]}
                for sequence, tile_index in enumerate(selected, 1)]
            progress("scheduled")
        else:
            last_ack = None
            for sequence, tile_index in enumerate(selected, 1):
                if last_ack is not None:
                    deadline = math.nextafter(last_ack + MIN_TILE_INTERVAL_SECONDS, math.inf)
                    sleep_checked(max(0.0, deadline - clock()))
                if not active():
                    raise RemoteEngineError("round_ended")
                sent = clock()
                room.select(expected_round, sequence, tile_index)
                last_ack = clock()
                report["selection_events"].append({"sequence": sequence, "tile_index": tile_index,
                                                    "sent_seconds": sent - started, "ack_seconds": last_ack - started})
            if not active():
                raise RemoteEngineError("round_ended")
            report["submit_sent_seconds"] = clock() - started
            result = room.submit(expected_round)
            report["submit_ack_seconds"] = clock() - started
            report.update(submit_sent=True, logical_submission_count=1, server_submission_observed=True)
            if type(result.get("correct")) is bool:
                report["submission_correct"] = result["correct"]
            if type(result.get("elapsedMs")) is int and result["elapsedMs"] >= 0:
                report["submission_elapsed_ms"] = result["elapsedMs"]
            progress("submitted")
            if PublicSnapshot.from_state(result.get("state"), room.lane).phase in TERMINAL_PHASES:
                report["status"] = "game_ended"
                return report
            pump.set_stage("submitted", snapshot=snapshot)
        # A wrong fixed attempt remains submitted, without output flipping or
        # re-inference. Keep the lease while the human finishes or time expires.
        while True:
            ensure_running()
            final = view()
            if final.round_id == expected_round and final.bot_attempted:
                report["server_submission_observed"] = True
                if pump.stage != "submitted":
                    progress("submitted")
                    if final.phase not in TERMINAL_PHASES:
                        pump.set_stage("submitted", snapshot=final)
            if final.phase in TERMINAL_PHASES:
                report["status"] = "game_ended"
                break
            if final.round_id != expected_round or final.round_number != expected_number:
                raise RemoteEngineError("round_ended")
            sleep_checked(0.25)
    except Exception as error:
        ended = isinstance(error, RemoteEngineError) and error.code == "round_ended"
        if isinstance(error, RemoteEngineError) and error.code == "round_changed" and "expected_round" in locals():
            try:
                latest = view()
                ended = latest.phase in TERMINAL_PHASES or latest.round_id != expected_round or latest.round_number != expected_number
            except Exception:
                pass
        cancelled_start = (isinstance(error, RemoteEngineError) and error.code in
                           {"start_request_changed", "queue_expired", "start_cancelled", "images_timeout", "image_load_timeout", "image_load_failed"}
                           and "expected_round" not in locals())
        report.update(status="game_ended" if ended else "start_cancelled" if cancelled_start else "aborted", error_type=type(error).__name__,
                      error_code=error.code if isinstance(error, RemoteEngineError) else "engine_failed")
        if report["status"] == "aborted":
            try:
                pump.set_stage("error", snapshot=snapshot if "snapshot" in locals() else None)
            except Exception:
                pass
    finally:
        if reservation is not None:
            released_at = clock()
            reservation.release()
            report.update(gpu_reservation_held_seconds=released_at - reservation.acquired_at,
                          gpu_released_monotonic_seconds=released_at,
                          gpu_reservation_released_seconds=released_at - started)
        if images is not None:
            for image in images:
                image.close()
        if owned_pump:
            pump.close()
        report["elapsed_seconds"] = clock() - started
        report["round_state_http_seconds"] = state_http_seconds
    return report


def run_room_session(room, models, *, report_sink, cancel=None, clock=time.monotonic, sleep=time.sleep,
                     wait_seconds=1800.0, heartbeat_factory=HeartbeatPump, progress=lambda _: None,
                     runner=run_one_room):
    """Reuse one capability and heartbeat across fresh rounds in the same room.

    The idle lobby/result wait is intentionally persistent. The bounded
    wait_seconds safety limit still applies to an active round, and --once
    continues to use run_one_room directly.
    """
    cancel = cancel or threading.Event()
    pump, attempted_rounds, attempted_requests = heartbeat_factory(room), set(), set()
    previous = None
    completed = 0
    try:
        current = room.view()
        pump.bind(current)
        pump.start()
        while not cancel.is_set():
            if pump.failed.is_set():
                raise RemoteEngineError("heartbeat_failed")
            current = room.view()
            request_id = current.start_request["id"] if current.start_request else None
            context = (current.phase, current.round_id, current.round_number, request_id)
            if current.phase == "expired":
                raise RemoteEngineError("room_expired")
            if ((current.phase == "queued" and request_id not in attempted_requests)
                    or (current.phase in {"loading", "countdown", "playing"} and current.round_id not in attempted_rounds)):
                report = runner(room, models, cancel=cancel, clock=clock, sleep=sleep,
                                wait_seconds=wait_seconds, progress=progress, pump=pump,
                                starting_snapshot=current, attempted_rounds=attempted_rounds,
                                attempted_requests=attempted_requests)
                report_sink(report)
                completed += 1
                if report.get("status") == "aborted":
                    return completed
                previous = None
                # Re-read rather than sending a result heartbeat with the old
                # context: a human can already have requested the next lobby.
                continue
            if context != previous:
                if current.phase == "lobby":
                    pump.set_stage("ready", snapshot=current)
                    progress("ready")
                elif current.phase == "countdown":
                    pump.set_stage("images_ready" if current.image_barrier_supported else "inferencing", snapshot=current)
                    progress("countdown")
                elif current.phase == "queued":
                    pump.set_stage("waiting_gpu", snapshot=current)
                    progress("waiting_gpu")
                else:
                    pump.set_stage("submitted", snapshot=current)
                    progress("waiting_next")
                previous = context
            sleep(0.5)
    finally:
        if cancel.is_set():
            try:
                pump.set_stage("error", snapshot=room.view())
            except Exception:
                pass
        pump.close()
    return completed


class LaneCancellation:
    def __init__(self, global_cancel, lane_cancel):
        self.global_cancel, self.lane_cancel = global_cancel, lane_cancel

    def is_set(self):
        return self.global_cancel.is_set() or self.lane_cancel.is_set()


class EngineController:
    """One active participant per lane with the configured shared-model slots."""

    def __init__(self, models, room_factory, output, *, wait_seconds=1800.0, progress=lambda *_: None,
                 runner=run_one_room, diagnostic=lambda *_: None, continuous=False):
        self.models, self.room_factory = models, room_factory
        self.output = Path(output)
        self.wait_seconds, self.progress, self.runner = wait_seconds, progress, runner
        self.diagnostic = diagnostic
        self.continuous = continuous
        self.cancel = threading.Event()
        self._lock = threading.Lock()
        self._workers, self._lane_cancel, self._counts, self.reports = {}, {}, {"A": 0, "B": 0}, []

    def _persist(self, lane, report):
        if isinstance(self.models, SharedModels):
            report.update(self.models.execution_metadata())
        with self._lock:
            self._counts[lane] += 1
            number = self._counts[lane]
        try:
            with (self.output / f"lane-{lane}-game-{number}.json").open("x", encoding="utf-8") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        except (OSError, ValueError, TypeError):
            report.update(status="aborted", error_code="report_write_failed")
        with self._lock:
            self.reports.append(report)
        self.progress(lane, "ended" if report.get("status") == "game_ended" else "start_cancelled" if report.get("status") == "start_cancelled" else "aborted")
        if report.get("status") == "aborted":
            self.diagnostic(lane, report.get("error_code", "engine_failed"))

    def add(self, lane, code):
        if lane not in {"A", "B"} or not isinstance(code, str) or not re.fullmatch(r"[A-Z2-9]{8}", code):
            raise ValueError("A/B와 해당 레인의 8자리 연결 코드가 필요합니다.")
        with self._lock:
            if self.cancel.is_set():
                raise RemoteEngineError("cancelled")
            previous = self._workers.get(lane)
            if previous is not None and previous.is_alive():
                raise RemoteEngineError("lane_busy")
            lane_cancel = threading.Event()
            self._lane_cancel[lane] = lane_cancel
            cancel = LaneCancellation(self.cancel, lane_cancel)
            def work():
                try:
                    room = self.room_factory(lane, code)
                    if self.continuous:
                        run_room_session(room, self.models, cancel=cancel, wait_seconds=self.wait_seconds,
                                         progress=lambda stage: self.progress(lane, stage), runner=self.runner,
                                         report_sink=lambda report: self._persist(lane, report))
                    else:
                        report = self.runner(room, self.models, cancel=cancel, wait_seconds=self.wait_seconds,
                                             progress=lambda stage: self.progress(lane, stage))
                        self._persist(lane, report)
                except Exception as error:
                    report = {"mode": "remote", "lane": lane, "status": "aborted",
                              "error_type": type(error).__name__,
                              "error_code": error.code if isinstance(error, RemoteEngineError) else "connection_failed",
                              "role_token_or_pairing_code_logged": False}
                    self._persist(lane, report)
            thread = threading.Thread(target=work, name=f"alpha-remote-{lane}", daemon=True)
            self._workers[lane] = thread
            thread.start()

    def stop(self, lane):
        if lane not in {"A", "B"}:
            raise ValueError("A/B lane required")
        with self._lock:
            event = self._lane_cancel.get(lane)
            worker = self._workers.get(lane)
            if event is None or worker is None or not worker.is_alive():
                raise RemoteEngineError("lane_not_connected")
            event.set()
        self.progress(lane, "stopping")

    def wait(self):
        with self._lock:
            workers = list(self._workers.values())
        for worker in workers:
            worker.join()

    def close(self):
        self.cancel.set()
        with self._lock:
            workers = list(self._workers.values())
        for worker in workers:
            worker.join(timeout=7)


def safe_diagnostic(code):
    return {
        "lane_busy": "이 레인은 연결 유지 중입니다. 같은 방은 패드의 다음 참가자 준비를 사용하세요. 다른 방으로 바꾸려면 먼저 stop A/B로 해당 연결을 중단하세요.",
        "lane_not_connected": "이 레인에는 중단할 활성 연결이 없습니다.",
        "protocol_upgrade_required": "서버와 PC 엔진의 출발·사진 준비 프로토콜이 맞지 않습니다. 최신 배포를 확인한 뒤 해당 레인을 다시 연결하세요.",
        "reservation_required": "GPU 예약 없이 시작된 문제를 중단했습니다. 사이트와 PC 엔진 버전을 확인하세요.",
        "lane_mismatch": "방의 A/B 레인과 입력한 레인이 다릅니다.",
        "invalid_mode": "인간 패드에서 원격 A/B 방을 새로 만들고 그 연결 코드를 사용하세요.",
        "engine_already_connected": "이미 엔진이 연결된 방입니다. 해당 레인의 새 방을 사용하세요.",
        "engine_not_ready": "서버가 엔진 준비 상태를 확인하지 못했습니다. 새 방으로 다시 연결하세요.",
        "not_found": "연결할 방이 없습니다. 패드에서 새 방을 만들고 코드를 확인하세요.",
        "room_expired": "방이 만료됐습니다. 새 참가자의 새 방을 사용하세요.",
        "connection_failed": "서버 연결이 끊겼습니다. 인터넷과 사이트 상태를 확인하세요.",
        "heartbeat_failed": "서버 생존 확인에 실패해 이 레인의 입력을 중단했습니다.",
        "wait_timeout": "경기 시작 또는 종료를 기다리는 제한 시간이 지났습니다.",
        "round_ended": "상대 정답 또는 시간 종료로 남은 입력을 중단했습니다.",
        "cancelled": "사용자가 엔진을 종료했습니다.",
        "report_write_failed": "실행 기록을 저장하지 못했습니다. 결과 폴더 권한과 여유 공간을 확인하세요.",
    }.get(code, "이 레인의 실행을 중단했습니다. 비밀값 없는 결과 보고서를 확인하세요.")

"""Mavis web server -- FastAPI backend with WebSocket pipeline and REST API.

Run with:
    uvicorn web.server:app --reload
    # or
    python -m web.server
"""

import asyncio
import base64
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mavis.audio import SAMPLE_RATE
from mavis.config import LAPTOP_CPU, MavisConfig
from mavis.difficulty import get_difficulty
from mavis.pipeline import create_pipeline
from mavis.scoring import ScoreTracker
from mavis.songs import Song, list_songs

from web.routers import songs

logger = logging.getLogger("mavis.web")


# --- Lifecycle (graceful shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("Mavis web server starting up")
    yield
    # Cleanup on shutdown
    logger.info("Mavis web server shutting down -- cleaning up %d sessions", len(_sessions))
    _sessions.clear()


app = FastAPI(
    title="Mavis",
    description="Vocal Typing Instrument - Web Interface",
    lifespan=lifespan,
)


# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "MAVIS_CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Rate Limiting (simple in-memory, per-IP) ---
_rate_limit_log: Dict[str, List[float]] = {}
_RATE_LIMIT_RPM = int(os.environ.get("MAVIS_RATE_LIMIT_RPM", "120"))
_WS_MAX_MESSAGE_SIZE = int(os.environ.get("MAVIS_WS_MAX_MSG_SIZE", "4096"))


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple per-IP rate limiting for HTTP endpoints."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60

    log = _rate_limit_log.get(client_ip, [])
    log = [t for t in log if t > window_start]

    if len(log) >= _RATE_LIMIT_RPM:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded. Try again later."},
        )

    log.append(now)
    _rate_limit_log[client_ip] = log
    return await call_next(request)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every HTTP request with method, path, status, and duration."""
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# --- Mount routers ---
app.include_router(songs.router)

# Mount static files
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "ok",
        "service": "mavis",
        "active_sessions": len(_sessions),
    }


# --- Active sessions ---

def _default_tts_backend() -> str:
    """Prefer real speech via espeak-ng when the binary is present."""
    import shutil
    return "espeak" if shutil.which("espeak-ng") else "mock"


def _default_llm_backend() -> str:
    """Prefer real G2P via espeak-ng when the binary is present.

    The "claude" and "llama" backends are opt-in (MAVIS_LLM_BACKEND) since
    they need an API key or a local model file.
    """
    import shutil
    return "espeak" if shutil.which("espeak-ng") else "mock"


class GameSession:
    """A per-client game session holding the pipeline and scoring state."""

    def __init__(self, difficulty: str = "medium", voice: str = "default"):
        self.session_id = str(uuid.uuid4())[:8]
        self.config = MavisConfig(
            hardware=LAPTOP_CPU,
            # Real G2P when espeak-ng is installed; MAVIS_LLM_BACKEND
            # overrides (e.g. "claude" for API-based conversion, "mock").
            llm_backend=os.environ.get("MAVIS_LLM_BACKEND", _default_llm_backend()),
            # Real speech when espeak-ng is installed; MAVIS_TTS_BACKEND=mock
            # forces the sine-wave synthesizer.
            tts_backend=os.environ.get("MAVIS_TTS_BACKEND", _default_tts_backend()),
            difficulty_name=difficulty,
            voice_name=voice,
        )
        self.pipeline = create_pipeline(self.config)
        try:
            self.tracker = ScoreTracker.from_difficulty(get_difficulty(difficulty))
        except KeyError:
            self.tracker = ScoreTracker()
        self.song: Optional[Song] = None
        self.phonemes_played = 0
        self.chars_typed = 0

    def feed_char(self, char: str, shift: bool = False, ctrl: bool = False):
        """Feed a character into the pipeline. Returns state dict.

        Keystrokes advance the pipeline with zero elapsed time: real time
        (and therefore buffer drain and scoring) is driven exclusively by
        the client's ~30fps idle ticks, so typing speed never changes the
        drain rate.
        """
        mods = {"shift": shift, "ctrl": ctrl, "alt": False}
        self.pipeline.feed(char, mods)
        self.chars_typed += 1

        state = self.pipeline.tick(elapsed_ms=0)
        return self._response(state)

    def tick_idle(self):
        """Advance the pipeline by one ~30fps frame of real time."""
        state = self.pipeline.tick(elapsed_ms=33)
        # Don't penalize the empty buffer before the player starts typing.
        if self.chars_typed > 0:
            self.tracker.on_tick(self.pipeline.output_buffer.state())
        return self._response(state)

    def _response(self, state: Dict) -> Dict:
        self.phonemes_played += state["phonemes_popped"]
        resp = {
            "input_level": state["input_buffer_level"],
            "input_size": state["input_buffer_size"],
            "output_level": state["output_buffer_level"],
            "output_status": state["output_buffer_status"],
            "output_size": state["output_buffer_size"],
            "last_phoneme": state["last_phoneme"],
            "last_tokens": state["last_tokens"],
            "score": self.tracker.score(),
            "grade": self.tracker.grade(),
            "phonemes_played": self.phonemes_played,
            "chars_typed": self.chars_typed,
        }
        audio = self.pipeline.take_audio()
        if audio:
            resp["audio"] = base64.b64encode(audio).decode("ascii")
            resp["sample_rate"] = SAMPLE_RATE
        return resp


_sessions: Dict[str, GameSession] = {}


# --- Serve main page ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page."""
    index_path = os.path.join(_static_dir, "index.html")
    with open(index_path) as f:
        return HTMLResponse(content=f.read())


# --- WebSocket helpers ---

def _validate_ws_message(raw: str):
    """Validate a WebSocket message. Returns (msg_dict, error_response)."""
    if len(raw) > _WS_MAX_MESSAGE_SIZE:
        return None, {"type": "error", "message": "Message too large"}
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return None, {"type": "error", "message": "Invalid JSON"}
    if not isinstance(msg, dict):
        return None, {"type": "error", "message": "Expected JSON object"}
    return msg, None


# --- WebSocket Gameplay ---

@app.websocket("/ws/play")
async def websocket_play(websocket: WebSocket):
    """WebSocket endpoint for real-time gameplay.

    Protocol:
        Client sends JSON messages:
            {"type": "start", "difficulty": "medium", "voice": "default", "song_id": "twinkle"}
            {"type": "key", "char": "a", "shift": false, "ctrl": false}
            {"type": "tick"}  -- idle tick (no input)
            {"type": "stop"}

        Server responds with JSON state after each key/tick:
            {"type": "state", ...pipeline state fields...}
            {"type": "result", "score": 100, "grade": "A", ...}
    """
    await websocket.accept()
    session: Optional[GameSession] = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg, err = _validate_ws_message(raw)
            if err:
                await websocket.send_json(err)
                continue
            msg_type = msg.get("type", "")

            if msg_type == "start":
                difficulty = msg.get("difficulty", "medium")
                voice = msg.get("voice", "default")
                session = GameSession(difficulty=difficulty, voice=voice)

                song_id = msg.get("song_id")
                if song_id:
                    song_list = list_songs("songs")
                    for s in song_list:
                        if s.song_id == song_id:
                            session.song = s
                            break

                # Network-backed G2P (claude): resolve the whole song's
                # vocabulary in one batch call up front so gameplay ticks
                # never wait on the API.
                if session.song is not None and hasattr(session.pipeline.llm, "prewarm"):
                    words = [t.text for t in session.song.tokens]
                    await asyncio.get_event_loop().run_in_executor(
                        None, session.pipeline.llm.prewarm, words
                    )

                _sessions[session.session_id] = session
                await websocket.send_json({
                    "type": "started",
                    "session_id": session.session_id,
                    "song": {
                        "title": session.song.title,
                        "sheet_text": session.song.sheet_text,
                        "bpm": session.song.bpm,
                        "difficulty": session.song.difficulty,
                    } if session.song else None,
                })

            elif msg_type == "key" and session is not None:
                char = msg.get("char", "")
                shift = msg.get("shift", False)
                ctrl = msg.get("ctrl", False)
                if char:
                    state = session.feed_char(char, shift=shift, ctrl=ctrl)
                    state["type"] = "state"
                    await websocket.send_json(state)

            elif msg_type == "tick" and session is not None:
                state = session.tick_idle()
                state["type"] = "state"
                await websocket.send_json(state)

            elif msg_type == "stop" and session is not None:
                result = {
                    "type": "result",
                    "score": session.tracker.score(),
                    "grade": session.tracker.grade(),
                    "phonemes_played": session.phonemes_played,
                    "chars_typed": session.chars_typed,
                }
                await websocket.send_json(result)
                _sessions.pop(session.session_id, None)
                session = None

    except WebSocketDisconnect:
        if session:
            _sessions.pop(session.session_id, None)
    except Exception:
        if session:
            _sessions.pop(session.session_id, None)


# --- Run directly ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)

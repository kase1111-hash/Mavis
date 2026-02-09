"""Mavis web server -- FastAPI backend with WebSocket pipeline and REST API.

Run with:
    uvicorn web.server:app --reload
    # or
    python -m web.server
"""

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

from mavis.config import LAPTOP_CPU, MavisConfig
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

class GameSession:
    """A per-client game session holding the pipeline and scoring state."""

    def __init__(self, difficulty: str = "medium", voice: str = "default"):
        self.session_id = str(uuid.uuid4())[:8]
        self.config = MavisConfig(
            hardware=LAPTOP_CPU,
            llm_backend="mock",
            tts_backend="mock",
            difficulty_name=difficulty,
            voice_name=voice,
        )
        self.pipeline = create_pipeline(self.config)
        self.tracker = ScoreTracker()
        self.song: Optional[Song] = None
        self.phonemes_played = 0
        self.chars_typed = 0

    def feed_char(self, char: str, shift: bool = False, ctrl: bool = False):
        """Feed a character and tick the pipeline. Returns state dict."""
        mods = {"shift": shift, "ctrl": ctrl, "alt": False}
        self.pipeline.feed(char, mods)
        self.chars_typed += 1

        state = self.pipeline.tick()
        buf_state = self.pipeline.output_buffer.state()
        self.tracker.on_tick(buf_state)

        if state["last_phoneme"]:
            self.phonemes_played += 1

        return {
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

    def tick_idle(self):
        """Tick the pipeline without input (drain buffer)."""
        state = self.pipeline.tick()
        buf_state = self.pipeline.output_buffer.state()
        self.tracker.on_tick(buf_state)

        if state["last_phoneme"]:
            self.phonemes_played += 1

        return {
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

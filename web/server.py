"""Mavis web server -- FastAPI backend with WebSocket pipeline and REST API.

Run with:
    uvicorn web.server:app --reload
    # or
    python -m web.server
"""

import asyncio
import json
import os
import sys
import uuid
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mavis.cloud import SyncPayload, UserStore, generate_token, verify_token
from mavis.config import LAPTOP_CPU, MavisConfig
from mavis.leaderboard import Leaderboard, LeaderboardEntry, get_default_leaderboard
from mavis.licensing import LicenseManager, list_tiers
from mavis.pipeline import create_pipeline, MavisPipeline
from mavis.researcher_api import APIKeyStore, PerformanceStore
from mavis.scoring import ScoreTracker
from mavis.song_browser import browse_songs
from mavis.song_editor import CommunityLibrary, SongDraft
from mavis.songs import Song, load_song, list_songs

app = FastAPI(title="Mavis", description="Vocal Typing Instrument - Web Interface")

# Mount static files
_static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")


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


# --- REST Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main page."""
    index_path = os.path.join(_static_dir, "index.html")
    with open(index_path) as f:
        return HTMLResponse(content=f.read())


@app.get("/api/songs")
async def get_songs(difficulty: Optional[str] = None):
    """List available songs, optionally filtered by difficulty."""
    songs = browse_songs("songs", difficulty=difficulty)
    return [
        {
            "song_id": s.song_id,
            "title": s.title,
            "bpm": s.bpm,
            "difficulty": s.difficulty,
            "token_count": len(s.tokens),
            "sheet_text": s.sheet_text,
        }
        for s in songs
    ]


@app.get("/api/songs/{song_id}")
async def get_song(song_id: str):
    """Get details for a specific song."""
    songs = list_songs("songs")
    for s in songs:
        if s.song_id == song_id:
            return {
                "song_id": s.song_id,
                "title": s.title,
                "bpm": s.bpm,
                "difficulty": s.difficulty,
                "sheet_text": s.sheet_text,
                "token_count": len(s.tokens),
            }
    return {"error": "Song not found"}


@app.get("/api/leaderboard/{song_id}")
async def get_leaderboard(song_id: str, difficulty: Optional[str] = None, limit: int = 10):
    """Get leaderboard for a song."""
    lb = get_default_leaderboard()
    scores = lb.get_scores(song_id, difficulty=difficulty, limit=limit)
    return {"song_id": song_id, "scores": scores}


@app.post("/api/leaderboard/{song_id}")
async def submit_score(song_id: str, data: dict):
    """Submit a score to the leaderboard."""
    lb = get_default_leaderboard()
    entry = LeaderboardEntry(
        player_name=data.get("player_name", "WebPlayer"),
        score=data.get("score", 0),
        grade=data.get("grade", "F"),
        song_id=song_id,
        difficulty=data.get("difficulty", "medium"),
        accuracy=data.get("accuracy", 0.0),
    )
    rank = lb.submit(entry)
    return {"rank": rank, "song_id": song_id}


# --- Auth Endpoints (Cloud Save) ---

_user_store = UserStore()
_community = CommunityLibrary()


@app.post("/auth/register")
async def auth_register(data: dict):
    """Register a new user account."""
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return {"error": "Username and password required"}
    if len(username) < 2 or len(username) > 20:
        return {"error": "Username must be 2-20 characters"}
    if len(password) < 4:
        return {"error": "Password must be at least 4 characters"}
    profile = _user_store.register(username, password)
    if profile is None:
        return {"error": "Username already taken"}
    token = generate_token(profile.user_id)
    return {"user_id": profile.user_id, "username": profile.username, "token": token}


@app.post("/auth/login")
async def auth_login(data: dict):
    """Authenticate and return a token."""
    username = data.get("username", "")
    password = data.get("password", "")
    profile = _user_store.authenticate(username, password)
    if profile is None:
        return {"error": "Invalid credentials"}
    token = generate_token(profile.user_id)
    return {"user_id": profile.user_id, "username": profile.username, "token": token}


@app.get("/api/profile")
async def get_profile(token: str = ""):
    """Get the authenticated user's profile."""
    user_id = verify_token(token)
    if user_id is None:
        return {"error": "Invalid or expired token"}
    profile = _user_store.get_user(user_id)
    if profile is None:
        return {"error": "User not found"}
    return profile.to_dict()


@app.put("/api/profile/voice")
async def update_voice(data: dict):
    """Update the user's voice preference."""
    user_id = verify_token(data.get("token", ""))
    if user_id is None:
        return {"error": "Invalid or expired token"}
    profile = _user_store.get_user(user_id)
    if profile is None:
        return {"error": "User not found"}
    profile.voice_preference = data.get("voice", "default")
    _user_store.update_user(profile)
    return {"ok": True}


@app.get("/api/progress")
async def get_progress(token: str = ""):
    """Get the user's tutorial progress and personal bests."""
    user_id = verify_token(token)
    if user_id is None:
        return {"error": "Invalid or expired token"}
    profile = _user_store.get_user(user_id)
    if profile is None:
        return {"error": "User not found"}
    return {
        "tutorial_progress": profile.tutorial_progress,
        "personal_bests": profile.personal_bests,
    }


@app.put("/api/progress")
async def sync_progress(data: dict):
    """Sync user progress (offline-first merge)."""
    user_id = verify_token(data.get("token", ""))
    if user_id is None:
        return {"error": "Invalid or expired token"}
    payload = SyncPayload(
        user_id=user_id,
        voice_preference=data.get("voice_preference", "default"),
        difficulty_preference=data.get("difficulty_preference", "medium"),
        tutorial_progress=data.get("tutorial_progress", {}),
        personal_bests=data.get("personal_bests", {}),
        leaderboard_entries=data.get("leaderboard_entries", []),
    )
    profile = _user_store.sync(payload)
    if profile is None:
        return {"error": "User not found"}
    return profile.to_dict()


# --- Community / User-Generated Content ---

@app.post("/api/songs/upload")
async def upload_song(data: dict):
    """Upload a community song (authenticated)."""
    user_id = verify_token(data.get("token", ""))
    if user_id is None:
        return {"error": "Authentication required"}
    profile = _user_store.get_user(user_id)
    author = profile.username if profile else "anonymous"
    draft = SongDraft(
        title=data.get("title", ""),
        bpm=data.get("bpm", 120),
        difficulty=data.get("difficulty", "medium"),
        sheet_text=data.get("sheet_text", ""),
        author=author,
        tags=data.get("tags", []),
    )
    errors = draft.validate()
    if errors:
        return {"error": errors}
    entry = _community.submit(draft, author=author)
    return {"entry_id": entry.entry_id, "title": draft.title}


@app.get("/api/songs/community")
async def browse_community(
    sort_by: str = "rating",
    difficulty: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Browse community-uploaded songs."""
    entries = _community.browse(
        sort_by=sort_by, difficulty=difficulty, limit=limit, offset=offset
    )
    return [e.to_dict() for e in entries]


@app.post("/api/songs/{entry_id}/rate")
async def rate_song(entry_id: str, data: dict):
    """Rate a community song (1-5 stars)."""
    rating = data.get("rating", 0)
    if _community.rate(entry_id, rating):
        return {"ok": True}
    return {"error": "Invalid rating or entry not found"}


@app.post("/api/songs/{entry_id}/flag")
async def flag_song(entry_id: str):
    """Flag a community song for moderation."""
    if _community.flag(entry_id):
        return {"ok": True}
    return {"error": "Entry not found"}


# --- Researcher API (Phase 4) ---

_perf_store = PerformanceStore()
_api_keys = APIKeyStore()
_license_mgr = LicenseManager()


def _check_api_key(api_key: str) -> Optional[str]:
    """Validate API key and check rate limit. Returns key_id or None."""
    key_id = _api_keys.validate(api_key)
    if key_id is None:
        return None
    if not _api_keys.check_rate_limit(key_id):
        return None
    return key_id


@app.post("/api/v1/register")
async def register_api_key(data: dict):
    """Register a new researcher API key."""
    owner = data.get("owner", "").strip()
    if not owner:
        return {"error": "Owner name required"}
    raw_key = _api_keys.register(owner)
    return {"api_key": raw_key, "owner": owner, "rate_limit": "100 requests/minute"}


@app.get("/api/v1/performances")
async def list_performances(
    api_key: str = "",
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Paginated list of anonymized performances."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    perfs = _perf_store.query(
        song_id=song_id, difficulty=difficulty,
        min_score=min_score, limit=limit, offset=offset,
    )
    return [p.to_dict() for p in perfs]


@app.get("/api/v1/performances/{perf_id}")
async def get_performance(perf_id: str, api_key: str = ""):
    """Full performance event stream."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    perf = _perf_store.get(perf_id)
    if perf is None:
        return {"error": "Performance not found"}
    return perf.to_dict()


@app.get("/api/v1/statistics")
async def get_statistics(api_key: str = ""):
    """Aggregate statistics across all performances."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    return _perf_store.statistics()


@app.get("/api/v1/prosody-map")
async def get_prosody_map(api_key: str = ""):
    """Aggregated text-to-prosody mappings across all performances."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    return _perf_store.prosody_map()


# --- Licensing Endpoints (Phase 4) ---

@app.get("/api/license/tiers")
async def get_license_tiers():
    """List available license tiers."""
    return list_tiers()


@app.get("/api/license/current")
async def get_current_license():
    """Get the current license status."""
    return _license_mgr.current().to_dict()


@app.post("/api/license/activate")
async def activate_license(data: dict):
    """Activate a license key."""
    key = data.get("key", "")
    info = _license_mgr.activate(key)
    if info is None:
        return {"error": "Invalid license key"}
    return info.to_dict()


@app.post("/api/license/deactivate")
async def deactivate_license():
    """Deactivate the current license."""
    _license_mgr.deactivate()
    return {"ok": True, "tier": "free"}


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
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "start":
                difficulty = msg.get("difficulty", "medium")
                voice = msg.get("voice", "default")
                session = GameSession(difficulty=difficulty, voice=voice)

                song_id = msg.get("song_id")
                if song_id:
                    songs = list_songs("songs")
                    for s in songs:
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


# --- Multiplayer WebSocket ---

class MultiplayerRoom:
    """A room for two players in competitive or duet mode."""

    def __init__(self, room_id: str, mode: str = "competitive"):
        self.room_id = room_id
        self.mode = mode  # "competitive" | "duet"
        self.players: Dict[str, dict] = {}  # ws_id -> {websocket, session}
        self.song: Optional[Song] = None

    @property
    def is_full(self) -> bool:
        return len(self.players) >= 2

    @property
    def player_count(self) -> int:
        return len(self.players)


_rooms: Dict[str, MultiplayerRoom] = {}


@app.post("/api/rooms")
async def create_room(data: dict):
    """Create a multiplayer room."""
    room_id = str(uuid.uuid4())[:6]
    mode = data.get("mode", "competitive")
    room = MultiplayerRoom(room_id=room_id, mode=mode)

    song_id = data.get("song_id")
    if song_id:
        songs = list_songs("songs")
        for s in songs:
            if s.song_id == song_id:
                room.song = s
                break

    _rooms[room_id] = room
    return {"room_id": room_id, "mode": mode}


@app.get("/api/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room status."""
    room = _rooms.get(room_id)
    if not room:
        return {"error": "Room not found"}
    return {
        "room_id": room.room_id,
        "mode": room.mode,
        "player_count": room.player_count,
        "is_full": room.is_full,
        "song": room.song.title if room.song else None,
    }


@app.websocket("/ws/room/{room_id}")
async def websocket_room(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for multiplayer rooms.

    Protocol:
        Client sends:
            {"type": "join", "player_name": "Alice", "difficulty": "medium", "voice": "default"}
            {"type": "key", "char": "a", "shift": false, "ctrl": false}
            {"type": "tick"}
            {"type": "leave"}

        Server broadcasts to all players:
            {"type": "player_joined", "player_name": "Alice", "player_count": 1}
            {"type": "state", "player": "Alice", ...state fields...}
            {"type": "opponent_state", "player": "Bob", ...state fields...}
            {"type": "result", "scores": {...}}
    """
    room = _rooms.get(room_id)
    if not room:
        await websocket.close(code=4004, reason="Room not found")
        return

    await websocket.accept()
    player_id = str(uuid.uuid4())[:8]
    player_name = "Player"
    session: Optional[GameSession] = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type", "")

            if msg_type == "join":
                if room.is_full:
                    await websocket.send_json({"type": "error", "message": "Room is full"})
                    continue

                player_name = msg.get("player_name", f"Player{room.player_count + 1}")
                difficulty = msg.get("difficulty", "medium")
                voice = msg.get("voice", "default")
                session = GameSession(difficulty=difficulty, voice=voice)
                session.song = room.song

                room.players[player_id] = {
                    "websocket": websocket,
                    "session": session,
                    "name": player_name,
                }

                # Notify all players
                for pid, pdata in room.players.items():
                    try:
                        await pdata["websocket"].send_json({
                            "type": "player_joined",
                            "player_name": player_name,
                            "player_count": room.player_count,
                            "song": {
                                "title": room.song.title,
                                "sheet_text": room.song.sheet_text,
                            } if room.song else None,
                        })
                    except Exception:
                        pass

            elif msg_type == "key" and session is not None:
                char = msg.get("char", "")
                shift = msg.get("shift", False)
                ctrl = msg.get("ctrl", False)
                if char:
                    state = session.feed_char(char, shift=shift, ctrl=ctrl)
                    state["type"] = "state"
                    state["player"] = player_name
                    await websocket.send_json(state)

                    # Broadcast opponent state to other players
                    opponent_state = dict(state)
                    opponent_state["type"] = "opponent_state"
                    for pid, pdata in room.players.items():
                        if pid != player_id:
                            try:
                                await pdata["websocket"].send_json(opponent_state)
                            except Exception:
                                pass

            elif msg_type == "tick" and session is not None:
                state = session.tick_idle()
                state["type"] = "state"
                state["player"] = player_name
                await websocket.send_json(state)

            elif msg_type == "leave":
                break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if player_id in room.players:
            del room.players[player_id]
            # Notify remaining players
            for pid, pdata in room.players.items():
                try:
                    await pdata["websocket"].send_json({
                        "type": "player_left",
                        "player_name": player_name,
                        "player_count": room.player_count,
                    })
                except Exception:
                    pass
            if room.player_count == 0:
                _rooms.pop(room_id, None)


# --- Run directly ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)

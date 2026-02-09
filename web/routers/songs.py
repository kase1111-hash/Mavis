"""Songs router -- song listing and leaderboard."""

from typing import Optional

from fastapi import APIRouter

from mavis.leaderboard import LeaderboardEntry, get_default_leaderboard
from mavis.song_browser import browse_songs
from mavis.songs import list_songs

router = APIRouter()


# --- Song Browsing ---

@router.get("/api/songs")
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


@router.get("/api/songs/{song_id}")
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


# --- Leaderboard ---

@router.get("/api/leaderboard/{song_id}")
async def get_leaderboard(song_id: str, difficulty: Optional[str] = None, limit: int = 10):
    """Get leaderboard for a song."""
    lb = get_default_leaderboard()
    scores = lb.get_scores(song_id, difficulty=difficulty, limit=limit)
    return {"song_id": song_id, "scores": scores}


@router.post("/api/leaderboard/{song_id}")
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

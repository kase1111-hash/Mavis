"""Songs router -- song listing, community library, leaderboard, and licensing."""

from typing import Optional

from fastapi import APIRouter, Header

from mavis.cloud import verify_token
from mavis.leaderboard import LeaderboardEntry, get_default_leaderboard
from mavis.licensing import LicenseManager, list_tiers
from mavis.song_browser import browse_songs
from mavis.song_editor import CommunityLibrary, SongDraft
from mavis.songs import list_songs

router = APIRouter()

_community = CommunityLibrary()
_license_mgr = LicenseManager()


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


@router.get("/api/songs/community")
async def browse_community_songs(
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


# --- Community UGC ---

@router.post("/api/songs/upload")
async def upload_song(data: dict, authorization: Optional[str] = Header(None)):
    """Upload a community song (authenticated)."""
    from web.routers.auth import _user_store, _get_user_id
    user_id = _get_user_id(authorization) or verify_token(data.get("token", ""))
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


@router.post("/api/songs/{entry_id}/rate")
async def rate_song(entry_id: str, data: dict):
    """Rate a community song (1-5 stars)."""
    rating = data.get("rating", 0)
    if _community.rate(entry_id, rating):
        return {"ok": True}
    return {"error": "Invalid rating or entry not found"}


@router.post("/api/songs/{entry_id}/flag")
async def flag_song(entry_id: str):
    """Flag a community song for moderation."""
    if _community.flag(entry_id):
        return {"ok": True}
    return {"error": "Entry not found"}


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


# --- Licensing ---

@router.get("/api/license/tiers")
async def get_license_tiers():
    """List available license tiers."""
    return list_tiers()


@router.get("/api/license/current")
async def get_current_license():
    """Get the current license status."""
    return _license_mgr.current().to_dict()


@router.post("/api/license/activate")
async def activate_license(data: dict):
    """Activate a license key."""
    key = data.get("key", "")
    info = _license_mgr.activate(key)
    if info is None:
        return {"error": "Invalid license key"}
    return info.to_dict()


@router.post("/api/license/deactivate")
async def deactivate_license():
    """Deactivate the current license."""
    _license_mgr.deactivate()
    return {"ok": True, "tier": "free"}

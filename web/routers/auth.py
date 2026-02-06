"""Auth router -- user registration, login, profile, and sync endpoints."""

from typing import Optional

from fastapi import APIRouter, Header

from mavis.cloud import SyncPayload, UserStore, generate_token, verify_token

router = APIRouter()

_user_store = UserStore()


def _get_user_id(authorization: Optional[str] = None) -> Optional[str]:
    """Extract and verify user_id from the Authorization header.

    Accepts: 'Bearer <token>' or plain '<token>'.
    """
    if not authorization:
        return None
    token = authorization
    if token.lower().startswith("bearer "):
        token = token[7:]
    return verify_token(token.strip())


@router.post("/auth/register")
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


@router.post("/auth/login")
async def auth_login(data: dict):
    """Authenticate and return a token."""
    username = data.get("username", "")
    password = data.get("password", "")
    profile = _user_store.authenticate(username, password)
    if profile is None:
        return {"error": "Invalid credentials"}
    token = generate_token(profile.user_id)
    return {"user_id": profile.user_id, "username": profile.username, "token": token}


@router.get("/api/profile")
async def get_profile(authorization: Optional[str] = Header(None), token: str = ""):
    """Get the authenticated user's profile.

    Accepts token via Authorization header (preferred) or query param (legacy).
    """
    user_id = _get_user_id(authorization) or verify_token(token)
    if user_id is None:
        return {"error": "Invalid or expired token"}
    profile = _user_store.get_user(user_id)
    if profile is None:
        return {"error": "User not found"}
    return profile.to_dict()


@router.put("/api/profile/voice")
async def update_voice(data: dict, authorization: Optional[str] = Header(None)):
    """Update the user's voice preference."""
    user_id = _get_user_id(authorization) or verify_token(data.get("token", ""))
    if user_id is None:
        return {"error": "Invalid or expired token"}
    profile = _user_store.get_user(user_id)
    if profile is None:
        return {"error": "User not found"}
    profile.voice_preference = data.get("voice", "default")
    _user_store.update_user(profile)
    return {"ok": True}


@router.get("/api/progress")
async def get_progress(authorization: Optional[str] = Header(None), token: str = ""):
    """Get the user's tutorial progress and personal bests."""
    user_id = _get_user_id(authorization) or verify_token(token)
    if user_id is None:
        return {"error": "Invalid or expired token"}
    profile = _user_store.get_user(user_id)
    if profile is None:
        return {"error": "User not found"}
    return {
        "tutorial_progress": profile.tutorial_progress,
        "personal_bests": profile.personal_bests,
    }


@router.put("/api/progress")
async def sync_progress(data: dict, authorization: Optional[str] = Header(None)):
    """Sync user progress (offline-first merge)."""
    user_id = _get_user_id(authorization) or verify_token(data.get("token", ""))
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

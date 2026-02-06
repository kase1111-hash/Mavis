"""Cloud save -- user accounts, authentication, and cross-device sync.

Provides an offline-first data model with sync endpoints for the FastAPI server.
Local data is always the source of truth; cloud sync happens when connected.

Dependencies (optional): bcrypt, python-jose (JWT), sqlalchemy
"""

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# --- Data models ---


@dataclass
class UserProfile:
    """A user account with game data."""

    user_id: str
    username: str
    password_hash: str = ""
    display_name: str = ""
    voice_preference: str = "default"
    difficulty_preference: str = "medium"
    tutorial_progress: Dict[int, str] = field(default_factory=dict)  # lesson_id -> grade
    personal_bests: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # song_id -> {score, grade}
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_sync: str = ""

    def to_dict(self) -> dict:
        """Serialize to a dictionary (excludes password_hash)."""
        d = asdict(self)
        d.pop("password_hash", None)
        return d


@dataclass
class SyncPayload:
    """Data exchanged during a cloud sync operation."""

    user_id: str
    voice_preference: str = "default"
    difficulty_preference: str = "medium"
    tutorial_progress: Dict[int, str] = field(default_factory=dict)
    personal_bests: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    leaderboard_entries: List[dict] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# --- Token management ---

import warnings as _warnings

_TOKEN_SECRET = os.environ.get("MAVIS_TOKEN_SECRET", "")
if not _TOKEN_SECRET:
    _warnings.warn(
        "MAVIS_TOKEN_SECRET not set -- using insecure dev default. "
        "Set this environment variable before any production deployment.",
        stacklevel=1,
    )
    _TOKEN_SECRET = "mavis-dev-secret"


def generate_token(user_id: str, secret: str = "", ttl_hours: int = 24) -> str:
    """Generate a simple authentication token.

    Uses HMAC-style token with expiry. In production, replace with proper JWT
    via python-jose.
    """
    secret = secret or _TOKEN_SECRET
    expires = int(time.time()) + (ttl_hours * 3600)
    payload = f"{user_id}:{expires}"
    sig = hashlib.sha256(f"{payload}:{secret}".encode()).hexdigest()[:16]
    return f"{payload}:{sig}"


def verify_token(token: str, secret: str = "") -> Optional[str]:
    """Verify a token and return the user_id, or None if invalid/expired."""
    secret = secret or _TOKEN_SECRET
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id, expires_str, sig = parts
        expires = int(expires_str)
        if time.time() > expires:
            return None
        expected_sig = hashlib.sha256(
            f"{user_id}:{expires_str}:{secret}".encode()
        ).hexdigest()[:16]
        if sig != expected_sig:
            return None
        return user_id
    except (ValueError, IndexError):
        return None


# --- Password hashing ---
# Uses bcrypt when available; falls back to iterated SHA-256 with HMAC.

try:
    import bcrypt as _bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


def hash_password(password: str) -> str:
    """Hash a password. Uses bcrypt if installed, otherwise iterated HMAC-SHA256."""
    if _HAS_BCRYPT:
        hashed = _bcrypt.hashpw(password.encode(), _bcrypt.gensalt())
        return f"bcrypt:{hashed.decode()}"
    # Fallback: iterated HMAC-SHA256 (100k rounds)
    salt = secrets.token_hex(16)
    h = _iterate_sha256(salt, password)
    return f"sha256:{salt}:{h}"


def check_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        if password_hash.startswith("bcrypt:"):
            if not _HAS_BCRYPT:
                return False
            stored = password_hash[len("bcrypt:"):].encode()
            return _bcrypt.checkpw(password.encode(), stored)
        if password_hash.startswith("sha256:"):
            _, salt, h = password_hash.split(":", 2)
            expected = _iterate_sha256(salt, password)
            return hmac.compare_digest(h, expected)
        # Legacy format (pre-upgrade): salt:hash
        salt, h = password_hash.split(":", 1)
        expected = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
        return hmac.compare_digest(h, expected)
    except (ValueError, TypeError):
        return False


def _iterate_sha256(salt: str, password: str, rounds: int = 100_000) -> str:
    """Iterated HMAC-SHA256 key derivation (fallback when bcrypt is unavailable)."""
    key = f"{salt}:{password}".encode()
    h = hashlib.sha256(key).digest()
    for _ in range(rounds - 1):
        h = hashlib.sha256(h + key).digest()
    return h.hex()


# --- Local user store (JSON file-based) ---


class UserStore:
    """File-based user storage at ~/.mavis/users.json.

    In production, replace with SQLAlchemy + PostgreSQL/SQLite.
    """

    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(os.path.expanduser("~"), ".mavis", "users.json")
        self.path = path
        self._users: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._users = data.get("users", {})
        else:
            self._users = {}

    def _save(self) -> None:
        dir_path = os.path.dirname(self.path) or "."
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"users": self._users}, f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            os.unlink(tmp)
            raise

    def register(self, username: str, password: str) -> Optional[UserProfile]:
        """Register a new user. Returns None if username already taken."""
        # Check for duplicate username
        for uid, udata in self._users.items():
            if udata.get("username", "").lower() == username.lower():
                return None

        user_id = secrets.token_hex(8)
        profile = UserProfile(
            user_id=user_id,
            username=username,
            password_hash=hash_password(password),
            display_name=username,
        )
        self._users[user_id] = asdict(profile)
        self._save()
        return profile

    def authenticate(self, username: str, password: str) -> Optional[UserProfile]:
        """Authenticate a user by username and password."""
        for uid, udata in self._users.items():
            if udata.get("username", "").lower() == username.lower():
                if check_password(password, udata.get("password_hash", "")):
                    return UserProfile(**udata)
                return None
        return None

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Look up a user by ID."""
        udata = self._users.get(user_id)
        if udata is None:
            return None
        return UserProfile(**udata)

    def update_user(self, profile: UserProfile) -> None:
        """Update a user's profile data."""
        self._users[profile.user_id] = asdict(profile)
        self._save()

    def sync(self, payload: SyncPayload) -> Optional[UserProfile]:
        """Merge a sync payload into the user's stored data.

        Uses last-write-wins for preferences and max-score-wins for bests.
        """
        profile = self.get_user(payload.user_id)
        if profile is None:
            return None

        # Preferences: take the incoming values
        profile.voice_preference = payload.voice_preference
        profile.difficulty_preference = payload.difficulty_preference

        # Tutorial progress: keep the better grade
        grade_order = {"S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
        for lid, grade in payload.tutorial_progress.items():
            lid_int = int(lid)
            existing = profile.tutorial_progress.get(lid_int, "")
            if grade_order.get(grade, 0) > grade_order.get(existing, 0):
                profile.tutorial_progress[lid_int] = grade

        # Personal bests: keep the higher score
        for song_id, best in payload.personal_bests.items():
            existing = profile.personal_bests.get(song_id, {})
            if best.get("score", 0) > existing.get("score", 0):
                profile.personal_bests[song_id] = best

        profile.last_sync = datetime.now(timezone.utc).isoformat()
        self.update_user(profile)
        return profile

    def user_count(self) -> int:
        """Return the total number of registered users."""
        return len(self._users)

    def list_users(self) -> List[UserProfile]:
        """Return all user profiles (without password hashes in display)."""
        return [UserProfile(**udata) for udata in self._users.values()]

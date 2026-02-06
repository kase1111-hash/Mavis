"""Researcher API -- anonymized performance data access with API key auth.

Provides a PerformanceStore for recording and querying anonymized performance
data, API key management, and rate limiting. Designed to be consumed by
the FastAPI server endpoints.
"""

import hashlib
import hmac as _hmac_mod
import json
import os
import secrets
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AnonymizedPerformance:
    """An anonymized performance record for researcher access."""

    perf_id: str
    song_id: str
    difficulty: str
    score: int
    grade: str
    token_count: int
    phoneme_count: int
    emotion: str
    features: List[float]  # 7-dim training features
    iml: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.perf_id,
            "song_id": self.song_id,
            "difficulty": self.difficulty,
            "score": self.score,
            "grade": self.grade,
            "token_count": self.token_count,
            "phoneme_count": self.phoneme_count,
            "emotion": self.emotion,
            "features": self.features,
            "iml": self.iml,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class PerformanceStore:
    """JSON-backed store of anonymized performance data.

    Stores performances stripped of player names and raw keystrokes.
    Only tokens, phonemes, scores, and IML data are retained.
    """

    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(
                os.path.expanduser("~"), ".mavis", "performances.json"
            )
        self.path = path
        self._performances: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._performances = data.get("performances", {})
        else:
            self._performances = {}

    def _save(self) -> None:
        dir_path = os.path.dirname(self.path) or "."
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"performances": self._performances}, f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            os.unlink(tmp)
            raise

    def record(self, perf: AnonymizedPerformance) -> str:
        """Store a performance. Returns the performance ID."""
        self._performances[perf.perf_id] = perf.to_dict()
        self._save()
        return perf.perf_id

    def get(self, perf_id: str) -> Optional[AnonymizedPerformance]:
        """Get a performance by ID."""
        data = self._performances.get(perf_id)
        if data is None:
            return None
        return AnonymizedPerformance(
            perf_id=data["id"],
            song_id=data["song_id"],
            difficulty=data["difficulty"],
            score=data["score"],
            grade=data["grade"],
            token_count=data["token_count"],
            phoneme_count=data["phoneme_count"],
            emotion=data["emotion"],
            features=data["features"],
            iml=data["iml"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )

    def query(
        self,
        song_id: Optional[str] = None,
        difficulty: Optional[str] = None,
        min_score: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[AnonymizedPerformance]:
        """Query performances with optional filters."""
        results = []
        for data in self._performances.values():
            if song_id and data.get("song_id") != song_id:
                continue
            if difficulty and data.get("difficulty") != difficulty:
                continue
            if min_score is not None and data.get("score", 0) < min_score:
                continue
            results.append(AnonymizedPerformance(
                perf_id=data["id"],
                song_id=data["song_id"],
                difficulty=data["difficulty"],
                score=data["score"],
                grade=data["grade"],
                token_count=data["token_count"],
                phoneme_count=data["phoneme_count"],
                emotion=data["emotion"],
                features=data["features"],
                iml=data["iml"],
                timestamp=data["timestamp"],
                metadata=data.get("metadata", {}),
            ))

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda p: p.timestamp, reverse=True)
        return results[offset: offset + limit]

    def statistics(self) -> Dict[str, Any]:
        """Compute aggregate statistics across all performances."""
        total = len(self._performances)
        if total == 0:
            return {
                "total_performances": 0,
                "songs": {},
                "difficulty_distribution": {},
                "emotion_distribution": {},
                "average_score": 0.0,
            }

        scores = []
        by_song: Dict[str, List[int]] = {}
        by_diff: Dict[str, int] = {}
        by_emotion: Dict[str, int] = {}

        for data in self._performances.values():
            s = data.get("score", 0)
            scores.append(s)

            sid = data.get("song_id", "unknown")
            by_song.setdefault(sid, []).append(s)

            d = data.get("difficulty", "unknown")
            by_diff[d] = by_diff.get(d, 0) + 1

            em = data.get("emotion", "neutral")
            by_emotion[em] = by_emotion.get(em, 0) + 1

        song_stats = {}
        for sid, song_scores in by_song.items():
            song_stats[sid] = {
                "count": len(song_scores),
                "average_score": round(sum(song_scores) / len(song_scores), 1),
                "max_score": max(song_scores),
            }

        return {
            "total_performances": total,
            "average_score": round(sum(scores) / len(scores), 1),
            "songs": song_stats,
            "difficulty_distribution": by_diff,
            "emotion_distribution": by_emotion,
        }

    def prosody_map(self) -> Dict[str, Any]:
        """Aggregate text-to-prosody mappings across all performances.

        Returns average feature vectors grouped by emotion label.
        """
        by_emotion: Dict[str, List[List[float]]] = {}

        for data in self._performances.values():
            em = data.get("emotion", "neutral")
            features = data.get("features", [])
            if len(features) == 7:
                by_emotion.setdefault(em, []).append(features)

        result = {}
        for em, feature_lists in by_emotion.items():
            n = len(feature_lists)
            avg = [0.0] * 7
            for fv in feature_lists:
                for i in range(7):
                    avg[i] += fv[i]
            avg = [round(v / n, 3) for v in avg]
            result[em] = {
                "count": n,
                "average_features": avg,
                "feature_labels": [
                    "mean_pitch_hz",
                    "pitch_range_hz",
                    "mean_volume",
                    "volume_range",
                    "mean_breathiness",
                    "speech_rate",
                    "vibrato_ratio",
                ],
            }

        return result

    def count(self) -> int:
        """Total number of stored performances."""
        return len(self._performances)


# --- API Key Management ---

@dataclass
class APIKey:
    """A researcher API key."""

    key_id: str
    key_hash: str  # salted SHA-256 hash of the actual key
    key_salt: str = ""  # salt for key hashing
    owner: str = ""
    created_at: str = ""
    requests_today: int = 0
    last_request_date: str = ""

    def to_dict(self) -> dict:
        return {
            "key_id": self.key_id,
            "key_hash": self.key_hash,
            "key_salt": self.key_salt,
            "owner": self.owner,
            "created_at": self.created_at,
            "requests_today": self.requests_today,
            "last_request_date": self.last_request_date,
        }


class APIKeyStore:
    """Manages researcher API keys with rate limiting."""

    RATE_LIMIT = 100  # requests per minute

    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(
                os.path.expanduser("~"), ".mavis", "api_keys.json"
            )
        self.path = path
        self._keys: Dict[str, dict] = {}
        self._request_log: Dict[str, List[float]] = {}  # key_id -> timestamps
        self._load()

    def _load(self) -> None:
        if os.path.isfile(self.path) and os.path.getsize(self.path) > 0:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._keys = data.get("keys", {})
            # Restore persisted rate limit timestamps
            now = time.time()
            window_start = now - 60
            for key_id, timestamps in data.get("rate_limits", {}).items():
                self._request_log[key_id] = [t for t in timestamps if t > window_start]
        else:
            self._keys = {}

    def _save(self) -> None:
        dir_path = os.path.dirname(self.path) or "."
        os.makedirs(dir_path, exist_ok=True)
        # Prune stale rate limit entries before persisting
        now = time.time()
        window_start = now - 60
        rate_limits = {}
        for key_id, timestamps in self._request_log.items():
            pruned = [t for t in timestamps if t > window_start]
            if pruned:
                rate_limits[key_id] = pruned
        fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"keys": self._keys, "rate_limits": rate_limits}, f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            os.unlink(tmp)
            raise

    def register(self, owner: str) -> str:
        """Register a new API key. Returns the plaintext key."""
        key_id = str(uuid.uuid4())[:8]
        raw_key = f"mavis_{key_id}_{uuid.uuid4().hex[:16]}"
        salt = secrets.token_hex(16)
        key_hash = hashlib.sha256(f"{salt}:{raw_key}".encode()).hexdigest()

        self._keys[key_id] = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            key_salt=salt,
            owner=owner,
            created_at=datetime.now(timezone.utc).isoformat(),
        ).to_dict()
        self._save()
        return raw_key

    def validate(self, raw_key: str) -> Optional[str]:
        """Validate an API key. Returns key_id if valid, None otherwise."""
        for key_id, data in self._keys.items():
            salt = data.get("key_salt", "")
            if salt:
                key_hash = hashlib.sha256(f"{salt}:{raw_key}".encode()).hexdigest()
            else:
                # Legacy unsalted keys
                key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            if _hmac_mod.compare_digest(data.get("key_hash", ""), key_hash):
                return key_id
        return None

    def check_rate_limit(self, key_id: str) -> bool:
        """Check if a key is within rate limits. Returns True if allowed."""
        now = time.time()
        window_start = now - 60  # 1-minute window

        log = self._request_log.get(key_id, [])
        # Prune old entries
        log = [t for t in log if t > window_start]
        self._request_log[key_id] = log

        if len(log) >= self.RATE_LIMIT:
            return False

        log.append(now)
        return True

    def revoke(self, key_id: str) -> bool:
        """Revoke an API key. Returns True if found and removed."""
        if key_id in self._keys:
            del self._keys[key_id]
            self._save()
            return True
        return False

    def list_keys(self) -> List[Dict[str, str]]:
        """List all registered API keys (without hashes)."""
        return [
            {"key_id": data["key_id"], "owner": data["owner"], "created_at": data["created_at"]}
            for data in self._keys.values()
        ]

    def key_count(self) -> int:
        """Total number of registered keys."""
        return len(self._keys)

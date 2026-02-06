"""Leaderboard -- local JSON-based high score storage."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class LeaderboardEntry:
    """A single leaderboard entry."""

    player_name: str
    score: int
    grade: str
    song_id: str
    difficulty: str
    accuracy: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Leaderboard:
    """In-memory leaderboard backed by a JSON file.

    Stores per-song high scores with a configurable maximum entries per song.
    """

    path: str
    max_entries_per_song: int = 10
    _entries: Dict[str, List[dict]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        """Load entries from the JSON file if it exists."""
        if os.path.isfile(self.path):
            with open(self.path, "r") as f:
                data = json.load(f)
            self._entries = data.get("songs", {})
        else:
            self._entries = {}

    def _save(self) -> None:
        """Persist entries to the JSON file (atomic write)."""
        dir_path = os.path.dirname(self.path) or "."
        os.makedirs(dir_path, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"songs": self._entries}, f, indent=2)
            os.replace(tmp, self.path)
        except BaseException:
            os.unlink(tmp)
            raise

    def submit(self, entry: LeaderboardEntry) -> int:
        """Submit a score and return its rank (1-based) within that song.

        Returns 0 if the score did not make the leaderboard.
        """
        song_key = entry.song_id
        entries = self._entries.setdefault(song_key, [])
        new = asdict(entry)

        entries.append(new)
        entries.sort(key=lambda e: e["score"], reverse=True)

        if len(entries) > self.max_entries_per_song:
            entries[:] = entries[: self.max_entries_per_song]

        self._save()

        # Determine rank
        for i, e in enumerate(entries):
            if (
                e["score"] == new["score"]
                and e["timestamp"] == new["timestamp"]
                and e["player_name"] == new["player_name"]
            ):
                return i + 1
        return 0

    def get_scores(
        self,
        song_id: str,
        difficulty: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]:
        """Return top scores for a song, optionally filtered by difficulty."""
        entries = self._entries.get(song_id, [])
        if difficulty is not None:
            entries = [e for e in entries if e.get("difficulty") == difficulty]
        return entries[:limit]

    def get_all_scores(self, limit_per_song: int = 5) -> Dict[str, List[dict]]:
        """Return top scores for every song."""
        result = {}
        for song_id, entries in self._entries.items():
            result[song_id] = entries[:limit_per_song]
        return result

    def clear(self, song_id: Optional[str] = None) -> None:
        """Clear scores for a specific song, or all scores."""
        if song_id is not None:
            self._entries.pop(song_id, None)
        else:
            self._entries.clear()
        self._save()

    def format_scores(self, song_id: str, limit: int = 10) -> str:
        """Format a song's leaderboard for terminal display."""
        entries = self.get_scores(song_id, limit=limit)
        if not entries:
            return "  (no scores yet)"
        lines = []
        for i, e in enumerate(entries, 1):
            name = e.get("player_name", "???")
            score = e.get("score", 0)
            grade = e.get("grade", "?")
            diff = e.get("difficulty", "?")
            lines.append(f"  {i:2d}. {name:<12s} {score:>8d}  [{grade}]  ({diff})")
        return "\n".join(lines)


def get_default_leaderboard() -> Leaderboard:
    """Return a Leaderboard using the default path (~/.mavis/leaderboards.json)."""
    home = os.path.expanduser("~")
    path = os.path.join(home, ".mavis", "leaderboards.json")
    return Leaderboard(path=path)

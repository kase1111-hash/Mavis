"""Song editor -- create, validate, and share user-generated songs.

Provides tools for creating new songs with Sheet Text, validating structure,
and managing a community song library with ratings and moderation.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mavis.storage import atomic_json_save, locked_json_load

from mavis.sheet_text import SheetTextToken, parse
from mavis.songs import Song


# --- Song Creation ---


@dataclass
class SongDraft:
    """A song being created or edited."""

    title: str = ""
    bpm: int = 120
    difficulty: str = "medium"
    sheet_text: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate the draft and return a list of errors (empty = valid)."""
        errors = []
        if not self.title.strip():
            errors.append("Title is required.")
        if self.bpm < 40 or self.bpm > 300:
            errors.append(f"BPM must be 40-300, got {self.bpm}.")
        if self.difficulty not in ("easy", "medium", "hard"):
            errors.append(f"Difficulty must be easy/medium/hard, got {self.difficulty!r}.")
        if not self.sheet_text.strip():
            errors.append("Sheet Text is required.")
        if len(self.sheet_text) > 5000:
            errors.append(f"Sheet Text too long ({len(self.sheet_text)} chars, max 5000).")
        return errors

    def to_song(self) -> Song:
        """Convert to a Song object, parsing the Sheet Text into tokens."""
        # Build char dicts from the sheet text
        chars = []
        for c in self.sheet_text:
            chars.append({
                "char": c,
                "shift": c.isupper(),
                "ctrl": False,
                "alt": False,
                "timestamp_ms": 0,
            })
        tokens = parse(chars)
        song_id = self.title.lower().replace(" ", "_").replace("'", "")[:32]
        return Song(
            title=self.title,
            bpm=self.bpm,
            difficulty=self.difficulty,
            sheet_text=self.sheet_text,
            tokens=tokens,
            song_id=song_id,
        )

    def to_json(self) -> dict:
        """Export as a song JSON dict (same format as songs/*.json)."""
        song = self.to_song()
        tokens_data = []
        for t in song.tokens:
            tokens_data.append({
                "text": t.text,
                "emphasis": t.emphasis,
                "sustain": t.sustain,
                "harmony": t.harmony,
                "duration_modifier": t.duration_modifier,
            })
        return {
            "title": self.title,
            "bpm": self.bpm,
            "difficulty": self.difficulty,
            "sheet_text": self.sheet_text,
            "tokens": tokens_data,
            "author": self.author,
            "tags": self.tags,
        }

    def save(self, path: str) -> None:
        """Save the draft as a JSON file."""
        data = self.to_json()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# --- Community Library ---


@dataclass
class CommunityEntry:
    """A song submitted to the community library."""

    entry_id: str
    song_data: dict
    author: str
    submitted_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    ratings: List[int] = field(default_factory=list)  # 1-5 stars
    flags: int = 0  # moderation flag count
    approved: bool = True

    @property
    def average_rating(self) -> float:
        if not self.ratings:
            return 0.0
        return sum(self.ratings) / len(self.ratings)

    @property
    def rating_count(self) -> int:
        return len(self.ratings)

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "title": self.song_data.get("title", ""),
            "author": self.author,
            "difficulty": self.song_data.get("difficulty", "medium"),
            "bpm": self.song_data.get("bpm", 120),
            "submitted_at": self.submitted_at,
            "average_rating": round(self.average_rating, 1),
            "rating_count": self.rating_count,
            "flags": self.flags,
            "approved": self.approved,
        }


class CommunityLibrary:
    """JSON-backed community song library.

    Stores uploaded songs with ratings and moderation status.
    """

    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(os.path.expanduser("~"), ".mavis", "community.json")
        self.path = path
        self._entries: Dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        data = locked_json_load(self.path)
        self._entries = data.get("entries", {}) if data else {}

    def _save(self) -> None:
        atomic_json_save(self.path, {"entries": self._entries})

    def submit(self, draft: SongDraft, author: str = "") -> CommunityEntry:
        """Submit a song to the community library. Returns the entry."""
        errors = draft.validate()
        if errors:
            raise ValueError(f"Invalid song: {'; '.join(errors)}")

        entry_id = str(uuid.uuid4())[:8]
        entry = CommunityEntry(
            entry_id=entry_id,
            song_data=draft.to_json(),
            author=author or draft.author,
        )
        self._entries[entry_id] = {
            "entry_id": entry.entry_id,
            "song_data": entry.song_data,
            "author": entry.author,
            "submitted_at": entry.submitted_at,
            "ratings": entry.ratings,
            "flags": entry.flags,
            "approved": entry.approved,
        }
        self._save()
        return entry

    def get_entry(self, entry_id: str) -> Optional[CommunityEntry]:
        """Look up an entry by ID."""
        data = self._entries.get(entry_id)
        if data is None:
            return None
        return CommunityEntry(**data)

    def browse(
        self,
        sort_by: str = "rating",
        difficulty: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[CommunityEntry]:
        """Browse community songs with filtering and sorting.

        sort_by: "rating" | "newest" | "title"
        """
        entries = []
        for data in self._entries.values():
            entry = CommunityEntry(**data)
            if not entry.approved:
                continue
            if difficulty and entry.song_data.get("difficulty") != difficulty:
                continue
            entries.append(entry)

        if sort_by == "rating":
            entries.sort(key=lambda e: e.average_rating, reverse=True)
        elif sort_by == "newest":
            entries.sort(key=lambda e: e.submitted_at, reverse=True)
        elif sort_by == "title":
            entries.sort(key=lambda e: e.song_data.get("title", "").lower())

        return entries[offset: offset + limit]

    def rate(self, entry_id: str, rating: int) -> bool:
        """Rate a song (1-5 stars). Returns True if successful."""
        if rating < 1 or rating > 5:
            return False
        data = self._entries.get(entry_id)
        if data is None:
            return False
        data.setdefault("ratings", []).append(rating)
        self._save()
        return True

    def flag(self, entry_id: str) -> bool:
        """Flag a song for moderation. Returns True if successful."""
        data = self._entries.get(entry_id)
        if data is None:
            return False
        data["flags"] = data.get("flags", 0) + 1
        # Auto-hide if flagged too many times
        if data["flags"] >= 3:
            data["approved"] = False
        self._save()
        return True

    def entry_count(self) -> int:
        """Total number of entries."""
        return len(self._entries)

    def approved_count(self) -> int:
        """Number of approved (visible) entries."""
        return sum(1 for d in self._entries.values() if d.get("approved", True))

"""Song loader -- parse song JSON files into Song dataclass."""

import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

from mavis.sheet_text import SheetTextToken


@dataclass
class Song:
    """A playable song with Sheet Text and expected token sequence."""

    title: str
    bpm: int
    difficulty: str  # "easy" | "medium" | "hard"
    sheet_text: str
    tokens: List[SheetTextToken] = field(default_factory=list)
    song_id: str = ""


def load_song(path: str) -> Song:
    """Load a song from a JSON file."""
    with open(path, "r") as f:
        data = json.load(f)

    tokens = []
    for t in data.get("tokens", []):
        tokens.append(
            SheetTextToken(
                text=t["text"],
                emphasis=t.get("emphasis", "none"),
                sustain=t.get("sustain", False),
                harmony=t.get("harmony", False),
                duration_modifier=t.get("duration_modifier", 1.0),
            )
        )

    song_id = os.path.splitext(os.path.basename(path))[0]
    return Song(
        title=data["title"],
        bpm=data["bpm"],
        difficulty=data["difficulty"],
        sheet_text=data["sheet_text"],
        tokens=tokens,
        song_id=song_id,
    )


def list_songs(directory: str) -> List[Song]:
    """List all songs in a directory."""
    songs = []
    if not os.path.isdir(directory):
        return songs
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".json"):
            songs.append(load_song(os.path.join(directory, filename)))
    return songs

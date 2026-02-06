"""Song browser -- list, filter, and select songs from the library."""

from typing import Dict, List, Optional

from mavis.songs import Song, list_songs


def browse_songs(
    directory: str = "songs",
    difficulty: Optional[str] = None,
) -> List[Song]:
    """Return songs from the library, optionally filtered by difficulty.

    Args:
        directory: Path to the songs directory.
        difficulty: If set, only return songs matching this difficulty
                    ("easy", "medium", "hard").

    Returns:
        List of Song objects sorted by difficulty then title.
    """
    songs = list_songs(directory)
    if difficulty is not None:
        songs = [s for s in songs if s.difficulty == difficulty]
    return sorted(songs, key=lambda s: (_difficulty_order(s.difficulty), s.title))


def group_by_difficulty(songs: List[Song]) -> Dict[str, List[Song]]:
    """Group a list of songs by their difficulty level.

    Returns:
        Dict mapping "easy"/"medium"/"hard" to lists of songs.
    """
    groups: Dict[str, List[Song]] = {"easy": [], "medium": [], "hard": []}
    for song in songs:
        groups.setdefault(song.difficulty, []).append(song)
    return groups


def song_summary(song: Song) -> str:
    """Return a one-line summary string for display in a song list.

    Format: ``[DIFFICULTY] Title (BPM bpm, N tokens)``
    """
    diff_label = song.difficulty.upper().ljust(6)
    return f"[{diff_label}] {song.title} ({song.bpm} bpm, {len(song.tokens)} tokens)"


def format_song_list(songs: List[Song]) -> str:
    """Format a numbered list of songs for terminal display."""
    if not songs:
        return "  (no songs found)"
    lines = []
    for i, song in enumerate(songs, 1):
        lines.append(f"  {i:2d}. {song_summary(song)}")
    return "\n".join(lines)


def _difficulty_order(difficulty: str) -> int:
    """Return a sort key for difficulty ordering."""
    return {"easy": 0, "medium": 1, "hard": 2}.get(difficulty, 3)

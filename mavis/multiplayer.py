"""Multiplayer module -- room management and duet song splitting.

Provides:
  - Room: manages two MavisPipeline instances for competitive or duet play
  - DuetSplitter: divides a song's Sheet Text into melody and harmony parts
  - RoomManager: creates, tracks, and cleans up multiplayer rooms
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from mavis.config import LAPTOP_CPU, MavisConfig
from mavis.pipeline import MavisPipeline, create_pipeline
from mavis.scoring import ScoreTracker
from mavis.sheet_text import SheetTextToken, parse
from mavis.songs import Song


# --- Duet Splitter ---


class DuetSplitter:
    """Split a song into two complementary parts for duet mode.

    Strategy: alternating lines for melody/harmony, with harmony tokens
    assigned to the second player and non-harmony tokens to the first.
    When no explicit harmony markers exist, splits by alternating phrases
    (sentences or lines).
    """

    @staticmethod
    def split(song: Song) -> Tuple[str, str]:
        """Split a song's sheet_text into (player1_text, player2_text).

        Player 1 gets the melody (non-harmony) lines.
        Player 2 gets the harmony ([bracketed]) lines and alternating phrases.
        """
        lines = song.sheet_text.split("\n")

        p1_lines = []
        p2_lines = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            # If the line contains harmony markers, send to player 2
            if "[" in stripped and "]" in stripped:
                p2_lines.append(stripped)
                # Give player 1 the line with harmony markers removed
                clean = stripped.replace("[", "").replace("]", "")
                p1_lines.append(clean)
            else:
                # Alternate non-harmony lines between players
                if i % 2 == 0:
                    p1_lines.append(stripped)
                    p2_lines.append("...")  # sustain/rest
                else:
                    p1_lines.append("...")  # sustain/rest
                    p2_lines.append(stripped)

        return ("\n".join(p1_lines), "\n".join(p2_lines))

    @staticmethod
    def split_tokens(tokens: List[SheetTextToken]) -> Tuple[List[SheetTextToken], List[SheetTextToken]]:
        """Split tokens into melody and harmony parts.

        Tokens with harmony=True go to player 2.
        Non-harmony tokens alternate between players.
        """
        p1_tokens = []
        p2_tokens = []
        non_harmony_count = 0

        for token in tokens:
            if token.harmony:
                p2_tokens.append(token)
                # Player 1 gets a normal version of the token
                p1_tokens.append(SheetTextToken(
                    text=token.text,
                    emphasis=token.emphasis,
                    sustain=token.sustain,
                    harmony=False,
                    duration_modifier=token.duration_modifier,
                ))
            else:
                if non_harmony_count % 2 == 0:
                    p1_tokens.append(token)
                else:
                    p2_tokens.append(token)
                non_harmony_count += 1

        return (p1_tokens, p2_tokens)


# --- Player ---


@dataclass
class Player:
    """A player in a multiplayer room."""

    player_id: str
    name: str
    pipeline: MavisPipeline
    tracker: ScoreTracker
    chars_typed: int = 0
    phonemes_played: int = 0
    ready: bool = False

    def feed_char(self, char: str, shift: bool = False, ctrl: bool = False) -> dict:
        """Feed a character and tick. Returns state dict."""
        mods = {"shift": shift, "ctrl": ctrl, "alt": False}
        self.pipeline.feed(char, mods)
        self.chars_typed += 1
        state = self.pipeline.tick()
        buf_state = self.pipeline.output_buffer.state()
        self.tracker.on_tick(buf_state)
        if state["last_phoneme"]:
            self.phonemes_played += 1
        return {
            "player": self.name,
            "score": self.tracker.score(),
            "grade": self.tracker.grade(),
            "output_level": state["output_buffer_level"],
            "output_status": state["output_buffer_status"],
            "chars_typed": self.chars_typed,
            "phonemes_played": self.phonemes_played,
        }

    def tick_idle(self) -> dict:
        """Tick without input."""
        state = self.pipeline.tick()
        buf_state = self.pipeline.output_buffer.state()
        self.tracker.on_tick(buf_state)
        if state["last_phoneme"]:
            self.phonemes_played += 1
        return {
            "player": self.name,
            "score": self.tracker.score(),
            "grade": self.tracker.grade(),
            "output_level": state["output_buffer_level"],
            "output_status": state["output_buffer_status"],
            "chars_typed": self.chars_typed,
            "phonemes_played": self.phonemes_played,
        }

    def result(self) -> dict:
        """Final results for this player."""
        return {
            "player": self.name,
            "score": self.tracker.score(),
            "grade": self.tracker.grade(),
            "chars_typed": self.chars_typed,
            "phonemes_played": self.phonemes_played,
        }


# --- Room ---


@dataclass
class Room:
    """A multiplayer room holding up to two players.

    Modes:
      - competitive: both players play the same song, highest score wins.
      - duet: song is split between players, combined output.
    """

    room_id: str
    mode: str = "competitive"  # "competitive" | "duet"
    song: Optional[Song] = None
    players: Dict[str, Player] = field(default_factory=dict)
    started: bool = False
    finished: bool = False

    @property
    def is_full(self) -> bool:
        return len(self.players) >= 2

    @property
    def player_count(self) -> int:
        return len(self.players)

    def add_player(
        self,
        name: str,
        difficulty: str = "medium",
        voice: str = "default",
    ) -> Player:
        """Add a player to the room. Returns the Player object."""
        if self.is_full:
            raise ValueError("Room is full")

        player_id = str(uuid.uuid4())[:8]
        config = MavisConfig(
            hardware=LAPTOP_CPU,
            llm_backend="mock",
            tts_backend="mock",
            difficulty_name=difficulty,
            voice_name=voice,
        )
        pipeline = create_pipeline(config)
        tracker = ScoreTracker()
        player = Player(
            player_id=player_id,
            name=name,
            pipeline=pipeline,
            tracker=tracker,
        )
        self.players[player_id] = player
        return player

    def remove_player(self, player_id: str) -> Optional[str]:
        """Remove a player from the room. Returns the player name or None."""
        player = self.players.pop(player_id, None)
        if player:
            return player.name
        return None

    def get_results(self) -> Dict[str, dict]:
        """Get final results for all players."""
        return {pid: p.result() for pid, p in self.players.items()}

    def get_winner(self) -> Optional[str]:
        """Return the name of the player with the highest score, or None for a tie."""
        if not self.players:
            return None
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: p.tracker.score(),
            reverse=True,
        )
        if len(sorted_players) < 2:
            return sorted_players[0].name
        if sorted_players[0].tracker.score() == sorted_players[1].tracker.score():
            return None  # Tie
        return sorted_players[0].name


# --- Room Manager ---


class RoomManager:
    """Manages multiplayer rooms."""

    def __init__(self):
        self._rooms: Dict[str, Room] = {}

    def create_room(
        self,
        mode: str = "competitive",
        song: Optional[Song] = None,
    ) -> Room:
        """Create a new room and return it."""
        room_id = str(uuid.uuid4())[:6]
        room = Room(room_id=room_id, mode=mode, song=song)
        self._rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """Look up a room by ID."""
        return self._rooms.get(room_id)

    def remove_room(self, room_id: str) -> None:
        """Remove a room."""
        self._rooms.pop(room_id, None)

    def active_rooms(self) -> List[Room]:
        """Return all rooms that have at least one player."""
        return [r for r in self._rooms.values() if r.player_count > 0]

    def room_count(self) -> int:
        """Total number of rooms."""
        return len(self._rooms)

    def cleanup_empty(self) -> int:
        """Remove all empty rooms. Returns count removed."""
        empty = [rid for rid, r in self._rooms.items() if r.player_count == 0]
        for rid in empty:
            del self._rooms[rid]
        return len(empty)

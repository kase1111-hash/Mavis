"""Scoring system -- tracks performance quality based on buffer management and accuracy."""

from typing import Dict, Optional

from mavis.difficulty import DifficultySettings
from mavis.output_buffer import BufferState
from mavis.sheet_text import SheetTextToken

# Default points per tick by buffer status (matches the Medium difficulty)
_TICK_POINTS = {
    "optimal": 10,
    "underflow": -5,
    "overflow": -3,
}

# Grade thresholds (minimum score for each grade)
_GRADES = [
    ("S", 0.90),
    ("A", 0.80),
    ("B", 0.70),
    ("C", 0.60),
    ("D", 0.50),
]


class ScoreTracker:
    """Track performance quality during a Mavis session.

    Points are awarded per tick for time in the optimal buffer zone
    and per token for matching expected Sheet Text markup. Point values
    default to the Medium difficulty; pass ``tick_points`` and
    ``token_bonus_multiplier`` (or use ``from_difficulty``) to customize.
    """

    def __init__(
        self,
        tick_points: Optional[Dict[str, int]] = None,
        token_bonus_multiplier: float = 1.0,
    ):
        self._tick_points = dict(_TICK_POINTS)
        if tick_points:
            self._tick_points.update(tick_points)
        self._token_bonus_multiplier = token_bonus_multiplier
        self._score: int = 0
        self._ticks: int = 0
        self._max_possible: int = 0
        self._token_matches: int = 0
        self._token_total: int = 0

    @classmethod
    def from_difficulty(cls, settings: DifficultySettings) -> "ScoreTracker":
        """Build a tracker using a difficulty preset's point values."""
        return cls(
            tick_points={
                "optimal": settings.tick_points_optimal,
                "underflow": settings.tick_points_underflow,
                "overflow": settings.tick_points_overflow,
            },
            token_bonus_multiplier=settings.token_bonus_multiplier,
        )

    def on_tick(self, buffer_state: BufferState) -> None:
        """Called each frame with the current output buffer state."""
        self._ticks += 1
        self._max_possible += self._tick_points["optimal"]
        self._score += self._tick_points.get(buffer_state.status, 0)

    def on_token(
        self,
        token: SheetTextToken,
        expected: Optional[SheetTextToken] = None,
    ) -> None:
        """Compare a typed token against an expected token for accuracy bonus."""
        if expected is None:
            return

        self._token_total += 1
        bonus = 0
        matches = 0
        checks = 0

        # Check emphasis match
        checks += 1
        if token.emphasis == expected.emphasis:
            matches += 1
            bonus += 50

        # Check sustain match
        checks += 1
        if token.sustain == expected.sustain:
            matches += 1
            bonus += 30

        # Check harmony match
        checks += 1
        if token.harmony == expected.harmony:
            matches += 1
            bonus += 20

        if matches == checks:
            self._token_matches += 1

        self._score += int(bonus * self._token_bonus_multiplier)

    def score(self) -> int:
        """Current total score (can be negative)."""
        return max(0, self._score)

    def grade(self) -> str:
        """Letter grade based on score ratio to max possible."""
        if self._max_possible <= 0:
            return "F"
        ratio = self._score / self._max_possible
        for letter, threshold in _GRADES:
            if ratio >= threshold:
                return letter
        return "F"

    def accuracy(self) -> float:
        """Token accuracy as a ratio (0.0 - 1.0)."""
        if self._token_total == 0:
            return 1.0
        return self._token_matches / self._token_total

    def reset(self) -> None:
        """Reset all scores to zero."""
        self._score = 0
        self._ticks = 0
        self._max_possible = 0
        self._token_matches = 0
        self._token_total = 0

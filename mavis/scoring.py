"""Scoring system -- tracks performance quality based on buffer management and accuracy."""

from typing import List, Optional

from mavis.output_buffer import BufferState
from mavis.sheet_text import SheetTextToken

# Points per tick by buffer status
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
    and per token for matching expected Sheet Text markup.
    """

    def __init__(self):
        self._score: int = 0
        self._ticks: int = 0
        self._max_possible: int = 0
        self._token_matches: int = 0
        self._token_total: int = 0

    def on_tick(self, buffer_state: BufferState) -> None:
        """Called each frame with the current output buffer state."""
        self._ticks += 1
        self._max_possible += _TICK_POINTS["optimal"]
        self._score += _TICK_POINTS.get(buffer_state.status, 0)

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

        self._score += bonus

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

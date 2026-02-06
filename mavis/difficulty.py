"""Difficulty system -- configurable difficulty levels that adjust gameplay parameters."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class DifficultySettings:
    """Gameplay parameters that vary by difficulty level.

    Attributes:
        name: Display name for the difficulty.
        input_buffer_capacity: Max chars in the input buffer.
        output_buffer_capacity: Max phonemes in the output buffer.
        optimal_zone_low: Lower threshold for optimal buffer zone (0.0-1.0).
        optimal_zone_high: Upper threshold for optimal buffer zone (0.0-1.0).
        tick_points_optimal: Points awarded per tick in optimal zone.
        tick_points_underflow: Points per tick in underflow.
        tick_points_overflow: Points per tick in overflow.
        token_bonus_multiplier: Multiplier on token match bonus points.
        drain_rate_multiplier: Multiplier on output buffer drain speed.
        description: Short description for UI display.
    """

    name: str
    input_buffer_capacity: int
    output_buffer_capacity: int
    optimal_zone_low: float
    optimal_zone_high: float
    tick_points_optimal: int
    tick_points_underflow: int
    tick_points_overflow: int
    token_bonus_multiplier: float
    drain_rate_multiplier: float
    description: str


# Predefined difficulty presets
EASY = DifficultySettings(
    name="Easy",
    input_buffer_capacity=512,
    output_buffer_capacity=256,
    optimal_zone_low=0.1,
    optimal_zone_high=0.9,
    tick_points_optimal=10,
    tick_points_underflow=-2,
    tick_points_overflow=-1,
    token_bonus_multiplier=1.0,
    drain_rate_multiplier=0.7,
    description="Wide buffer zone, gentle penalties. Great for learning.",
)

MEDIUM = DifficultySettings(
    name="Medium",
    input_buffer_capacity=256,
    output_buffer_capacity=128,
    optimal_zone_low=0.2,
    optimal_zone_high=0.8,
    tick_points_optimal=10,
    tick_points_underflow=-5,
    tick_points_overflow=-3,
    token_bonus_multiplier=1.5,
    drain_rate_multiplier=1.0,
    description="Standard buffer zone and penalties. The intended experience.",
)

HARD = DifficultySettings(
    name="Hard",
    input_buffer_capacity=128,
    output_buffer_capacity=64,
    optimal_zone_low=0.3,
    optimal_zone_high=0.7,
    tick_points_optimal=15,
    tick_points_underflow=-10,
    tick_points_overflow=-7,
    token_bonus_multiplier=2.0,
    drain_rate_multiplier=1.4,
    description="Narrow buffer zone, harsh penalties. For experienced players.",
)

EXPERT = DifficultySettings(
    name="Expert",
    input_buffer_capacity=64,
    output_buffer_capacity=32,
    optimal_zone_low=0.35,
    optimal_zone_high=0.65,
    tick_points_optimal=20,
    tick_points_underflow=-15,
    tick_points_overflow=-12,
    token_bonus_multiplier=3.0,
    drain_rate_multiplier=1.8,
    description="Razor-thin buffer zone. Only for virtuosos.",
)

DIFFICULTY_PRESETS: Dict[str, DifficultySettings] = {
    "easy": EASY,
    "medium": MEDIUM,
    "hard": HARD,
    "expert": EXPERT,
}


def get_difficulty(name: str) -> DifficultySettings:
    """Look up a difficulty preset by name (case-insensitive).

    Raises:
        KeyError: If the difficulty name is not recognized.
    """
    key = name.lower()
    if key not in DIFFICULTY_PRESETS:
        valid = ", ".join(sorted(DIFFICULTY_PRESETS))
        raise KeyError(f"Unknown difficulty {name!r}. Valid: {valid}")
    return DIFFICULTY_PRESETS[key]


def list_difficulties() -> list:
    """Return all difficulty presets in order of increasing challenge."""
    return [EASY, MEDIUM, HARD, EXPERT]

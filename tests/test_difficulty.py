"""Tests for mavis.difficulty."""

import pytest

from mavis.difficulty import (
    DIFFICULTY_PRESETS,
    EASY,
    EXPERT,
    HARD,
    MEDIUM,
    DifficultySettings,
    get_difficulty,
    list_difficulties,
)


def test_preset_count():
    assert len(DIFFICULTY_PRESETS) == 4


def test_easy_wider_zone_than_hard():
    zone_easy = EASY.optimal_zone_high - EASY.optimal_zone_low
    zone_hard = HARD.optimal_zone_high - HARD.optimal_zone_low
    assert zone_easy > zone_hard


def test_expert_narrowest_zone():
    zone_expert = EXPERT.optimal_zone_high - EXPERT.optimal_zone_low
    for name, ds in DIFFICULTY_PRESETS.items():
        if name == "expert":
            continue
        zone = ds.optimal_zone_high - ds.optimal_zone_low
        assert zone > zone_expert, f"{name} should have wider zone than expert"


def test_get_difficulty_case_insensitive():
    d1 = get_difficulty("Easy")
    d2 = get_difficulty("EASY")
    d3 = get_difficulty("easy")
    assert d1.name == d2.name == d3.name


def test_get_difficulty_unknown():
    with pytest.raises(KeyError):
        get_difficulty("impossible")


def test_list_difficulties_order():
    diffs = list_difficulties()
    assert len(diffs) == 4
    assert diffs[0].name == "Easy"
    assert diffs[-1].name == "Expert"


def test_penalty_scaling():
    # Harder difficulties should have harsher penalties
    assert EASY.tick_points_underflow > MEDIUM.tick_points_underflow
    assert MEDIUM.tick_points_underflow > HARD.tick_points_underflow


def test_buffer_capacity_decreases():
    assert EASY.output_buffer_capacity > MEDIUM.output_buffer_capacity
    assert MEDIUM.output_buffer_capacity > HARD.output_buffer_capacity
    assert HARD.output_buffer_capacity > EXPERT.output_buffer_capacity


def test_drain_rate_increases():
    assert EASY.drain_rate_multiplier < MEDIUM.drain_rate_multiplier
    assert MEDIUM.drain_rate_multiplier < HARD.drain_rate_multiplier


def test_token_bonus_multiplier_increases():
    assert EASY.token_bonus_multiplier < MEDIUM.token_bonus_multiplier
    assert MEDIUM.token_bonus_multiplier < HARD.token_bonus_multiplier

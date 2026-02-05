"""Tests for mavis.scoring."""

from mavis.output_buffer import BufferState
from mavis.scoring import ScoreTracker
from mavis.sheet_text import SheetTextToken


def _buf(status="optimal"):
    return BufferState(level=0.5, status=status, drain_rate=0.0, fill_rate=0.0)


def _token(emphasis="none", sustain=False, harmony=False):
    return SheetTextToken(text="test", emphasis=emphasis, sustain=sustain, harmony=harmony)


def test_optimal_ticks_positive_score():
    tracker = ScoreTracker()
    for _ in range(100):
        tracker.on_tick(_buf("optimal"))
    assert tracker.score() > 0
    assert tracker.grade() == "S"


def test_underflow_ticks_low_score():
    tracker = ScoreTracker()
    for _ in range(100):
        tracker.on_tick(_buf("underflow"))
    assert tracker.score() == 0  # clamped to 0
    assert tracker.grade() == "F"


def test_overflow_ticks_reduce_score():
    tracker = ScoreTracker()
    for _ in range(100):
        tracker.on_tick(_buf("overflow"))
    assert tracker.grade() == "F"


def test_token_match_bonus():
    tracker = ScoreTracker()
    for _ in range(10):
        tracker.on_tick(_buf("optimal"))
    expected = _token(emphasis="loud", sustain=True, harmony=False)
    actual = _token(emphasis="loud", sustain=True, harmony=False)
    tracker.on_token(actual, expected)
    score_after = tracker.score()
    assert score_after > 100  # tick points + full match bonus


def test_token_mismatch():
    tracker = ScoreTracker()
    expected = _token(emphasis="loud")
    actual = _token(emphasis="none")
    tracker.on_token(actual, expected)
    # Only sustain and harmony match, emphasis does not
    assert tracker.score() > 0  # partial bonus from sustain+harmony match


def test_no_expected_token():
    tracker = ScoreTracker()
    tracker.on_token(_token(), None)
    assert tracker.score() == 0


def test_accuracy_all_match():
    tracker = ScoreTracker()
    t = _token(emphasis="loud")
    tracker.on_token(t, t)
    assert tracker.accuracy() == 1.0


def test_accuracy_no_tokens():
    tracker = ScoreTracker()
    assert tracker.accuracy() == 1.0


def test_reset():
    tracker = ScoreTracker()
    for _ in range(10):
        tracker.on_tick(_buf("optimal"))
    tracker.reset()
    assert tracker.score() == 0
    assert tracker.grade() == "F"

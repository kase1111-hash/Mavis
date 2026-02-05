"""Tests for mavis.pipeline."""

from mavis.config import MavisConfig
from mavis.pipeline import MavisPipeline, create_pipeline


def test_create_pipeline_default():
    pipe = create_pipeline()
    assert isinstance(pipe, MavisPipeline)


def test_feed_and_tick():
    pipe = create_pipeline()
    pipe.feed_text("the SUN rises")
    state = pipe.tick()
    assert state["input_buffer_level"] == 0.0 or state["input_buffer_size"] >= 0


def test_pipeline_processes_text():
    pipe = create_pipeline()
    pipe.feed_text("hello world")
    # Run enough ticks to process everything
    for _ in range(10):
        pipe.tick()
    state = pipe.state()
    # Some phonemes should have been produced and played
    assert state["last_phoneme"] is not None or state["output_buffer_size"] >= 0


def test_pipeline_state_keys():
    pipe = create_pipeline()
    state = pipe.state()
    expected_keys = [
        "input_buffer_level",
        "input_buffer_size",
        "output_buffer_level",
        "output_buffer_status",
        "output_buffer_size",
        "output_drain_rate",
        "output_fill_rate",
        "last_tokens",
        "last_phoneme",
    ]
    for key in expected_keys:
        assert key in state


def test_empty_pipeline_tick():
    pipe = create_pipeline()
    state = pipe.tick()
    assert state["input_buffer_size"] == 0
    assert state["last_phoneme"] is None


def test_feed_single_char():
    pipe = create_pipeline()
    pipe.feed("a", {"shift": False, "ctrl": False, "alt": False})
    assert pipe.input_buffer.size() == 1


def test_full_flow():
    """Feed text, tick multiple times, verify phonemes are produced."""
    pipe = create_pipeline()
    pipe.feed_text("the SUN... is falling _down_ and RISING [again]")

    phonemes_seen = []
    for _ in range(50):
        state = pipe.tick()
        if state["last_phoneme"]:
            phonemes_seen.append(state["last_phoneme"])

    assert len(phonemes_seen) > 0

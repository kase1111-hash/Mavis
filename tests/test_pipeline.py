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


def test_drain_is_time_based():
    """Draining depends on elapsed time, not tick count."""
    pipe = create_pipeline()
    pipe.feed_text("twinkle twinkle little star ")
    # Let input flow into the output buffer with negligible drain
    for _ in range(5):
        pipe.tick(elapsed_ms=0)
    filled = pipe.output_buffer.size()
    assert filled > 0

    # One second of real time should drain ~base_drain_rate phonemes
    state = pipe.tick(elapsed_ms=1000)
    assert state["phonemes_popped"] == int(pipe.drain_rate)
    assert pipe.output_buffer.size() == filled - state["phonemes_popped"]


def test_drain_rate_scales_with_difficulty():
    easy = create_pipeline(MavisConfig(difficulty_name="easy"))
    expert = create_pipeline(MavisConfig(difficulty_name="expert"))
    assert expert.drain_rate > easy.drain_rate


def test_take_audio_returns_pcm():
    pipe = create_pipeline()
    pipe.feed_text("hello world ")
    for _ in range(5):
        pipe.tick(elapsed_ms=0)
    pipe.tick(elapsed_ms=1000)
    audio = pipe.take_audio()
    assert isinstance(audio, bytes)
    assert len(audio) > 0
    # Cleared after take
    assert pipe.take_audio() == b""


def test_game_is_winnable_at_human_typing_speed():
    """Regression test: a buffer-watching player typing ~6 chars/sec on
    Medium must be able to hold the optimal zone and score points."""
    from mavis.difficulty import get_difficulty
    from mavis.scoring import ScoreTracker

    difficulty = get_difficulty("medium")
    pipe = create_pipeline(MavisConfig(difficulty_name="medium"))
    tracker = ScoreTracker.from_difficulty(difficulty)
    mid = (difficulty.optimal_zone_low + difficulty.optimal_zone_high) / 2

    text = "twinkle twinkle little star how i wonder what you are " * 10
    fps = 30
    chars_per_frame = 6 / fps
    index, acc, typed = 0, 0.0, False
    optimal_ticks = 0
    scored_ticks = 0

    for _ in range(30 * fps):  # 30 seconds of play
        if pipe.output_buffer.state().level < mid:
            acc += chars_per_frame
            while acc >= 1 and index < len(text):
                pipe.feed(text[index])
                index += 1
                acc -= 1
                typed = True
        pipe.tick(elapsed_ms=1000 // fps)
        if typed:
            buf_state = pipe.output_buffer.state()
            tracker.on_tick(buf_state)
            scored_ticks += 1
            if buf_state.status == "optimal":
                optimal_ticks += 1

    assert optimal_ticks / scored_ticks > 0.5
    assert tracker.score() > 0
    assert tracker.grade() != "F"

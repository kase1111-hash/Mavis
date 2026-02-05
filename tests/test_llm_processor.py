"""Tests for mavis.llm_processor."""

import pytest

from mavis.llm_processor import (
    ClaudeLLMProcessor,
    LlamaLLMProcessor,
    MockLLMProcessor,
    PhonemeEvent,
)
from mavis.sheet_text import SheetTextToken


def _token(text, emphasis="none", sustain=False, harmony=False, dur=1.0):
    return SheetTextToken(text=text, emphasis=emphasis, sustain=sustain,
                          harmony=harmony, duration_modifier=dur)


def test_mock_basic_conversion():
    proc = MockLLMProcessor()
    tokens = [_token("hello")]
    events = proc.process(tokens)
    assert len(events) > 0
    assert all(isinstance(e, PhonemeEvent) for e in events)


def test_loud_volume():
    proc = MockLLMProcessor()
    events = proc.process([_token("sun", emphasis="loud")])
    for e in events:
        assert e.volume > 0.7


def test_soft_breathiness():
    proc = MockLLMProcessor()
    events = proc.process([_token("gently", emphasis="soft")])
    for e in events:
        assert e.breathiness > 0.5
        assert e.volume < 0.4


def test_sustain_vibrato():
    proc = MockLLMProcessor()
    events = proc.process([_token("hold", sustain=True, dur=2.0)])
    for e in events:
        assert e.vibrato is True
        assert e.duration_ms == 200  # base 100 * 2.0


def test_harmony_intervals():
    proc = MockLLMProcessor()
    events = proc.process([_token("together", harmony=True)])
    for e in events:
        assert len(e.harmony_intervals) > 0
        assert 4 in e.harmony_intervals
        assert 7 in e.harmony_intervals


def test_sequential_non_overlapping():
    proc = MockLLMProcessor()
    events = proc.process([_token("hello"), _token("world")])
    for i in range(1, len(events)):
        assert events[i].start_ms >= events[i - 1].start_ms + events[i - 1].duration_ms


def test_shout_max_volume():
    proc = MockLLMProcessor()
    events = proc.process([_token("stop", emphasis="shout")])
    for e in events:
        assert e.volume == 1.0


def test_empty_tokens():
    proc = MockLLMProcessor()
    events = proc.process([])
    assert events == []


def test_llama_stub_raises():
    proc = LlamaLLMProcessor("/fake/model")
    with pytest.raises(NotImplementedError):
        proc.process([_token("test")])


def test_claude_stub_raises():
    proc = ClaudeLLMProcessor("fake-key")
    with pytest.raises(NotImplementedError):
        proc.process([_token("test")])

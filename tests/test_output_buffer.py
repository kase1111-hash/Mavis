"""Tests for mavis.output_buffer."""

from mavis.llm_processor import PhonemeEvent
from mavis.output_buffer import OutputBuffer


def _event(phoneme="ah", duration_ms=100):
    return PhonemeEvent(phoneme=phoneme, duration_ms=duration_ms)


def test_empty_state():
    buf = OutputBuffer(capacity=10)
    state = buf.state()
    assert state.level == 0.0
    assert state.status == "underflow"


def test_push_increases_level():
    buf = OutputBuffer(capacity=10)
    buf.push([_event() for _ in range(5)])
    state = buf.state()
    assert state.level == 0.5
    assert state.status == "optimal"


def test_pop_decreases_level():
    buf = OutputBuffer(capacity=10)
    buf.push([_event() for _ in range(5)])
    buf.pop()
    assert buf.size() == 4


def test_pop_empty_returns_none():
    buf = OutputBuffer(capacity=10)
    assert buf.pop() is None


def test_overflow_status():
    buf = OutputBuffer(capacity=10)
    buf.push([_event() for _ in range(9)])
    state = buf.state()
    assert state.level > 0.8
    assert state.status == "overflow"


def test_capacity_limit():
    buf = OutputBuffer(capacity=5)
    buf.push([_event() for _ in range(10)])
    assert buf.size() == 5  # only first 5 fit


def test_pop_returns_fifo_order():
    buf = OutputBuffer(capacity=10)
    buf.push([PhonemeEvent(phoneme="a"), PhonemeEvent(phoneme="b")])
    assert buf.pop().phoneme == "a"
    assert buf.pop().phoneme == "b"


def test_clear():
    buf = OutputBuffer(capacity=10)
    buf.push([_event() for _ in range(5)])
    buf.clear()
    assert buf.size() == 0
    assert buf.state().status == "underflow"


def test_state_rate_fields_exist():
    buf = OutputBuffer(capacity=10)
    state = buf.state()
    assert hasattr(state, "drain_rate")
    assert hasattr(state, "fill_rate")
    assert state.drain_rate >= 0.0
    assert state.fill_rate >= 0.0

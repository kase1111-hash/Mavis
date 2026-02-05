"""Tests for mavis.input_buffer."""

from mavis.input_buffer import InputBuffer


def test_push_and_consume_order():
    buf = InputBuffer(capacity=10)
    buf.push("a")
    buf.push("b")
    buf.push("c")
    items = buf.consume(3)
    assert [i["char"] for i in items] == ["a", "b", "c"]


def test_level_empty():
    buf = InputBuffer(capacity=10)
    assert buf.level() == 0.0


def test_level_full():
    buf = InputBuffer(capacity=4)
    for c in "abcd":
        buf.push(c)
    assert buf.level() == 1.0


def test_level_partial():
    buf = InputBuffer(capacity=10)
    buf.push("a")
    buf.push("b")
    assert buf.level() == 0.2


def test_overflow_drops_oldest():
    buf = InputBuffer(capacity=3)
    for c in "abcde":
        buf.push(c)
    # Only the last 3 should remain
    items = buf.consume(3)
    assert [i["char"] for i in items] == ["c", "d", "e"]


def test_modifier_flags():
    buf = InputBuffer()
    buf.push("A", {"shift": True, "ctrl": False, "alt": False})
    buf.push("b", {"shift": False, "ctrl": True, "alt": False})
    items = buf.consume(2)
    assert items[0]["shift"] is True
    assert items[0]["ctrl"] is False
    assert items[1]["ctrl"] is True


def test_default_modifiers():
    buf = InputBuffer()
    buf.push("x")
    items = buf.consume(1)
    assert items[0]["shift"] is False
    assert items[0]["ctrl"] is False
    assert items[0]["alt"] is False


def test_peek_does_not_consume():
    buf = InputBuffer()
    buf.push("a")
    buf.push("b")
    peeked = buf.peek(2)
    assert len(peeked) == 2
    assert buf.size() == 2


def test_consume_more_than_available():
    buf = InputBuffer()
    buf.push("a")
    items = buf.consume(5)
    assert len(items) == 1


def test_size():
    buf = InputBuffer()
    assert buf.size() == 0
    buf.push("x")
    assert buf.size() == 1


def test_clear():
    buf = InputBuffer()
    buf.push("a")
    buf.push("b")
    buf.clear()
    assert buf.size() == 0
    assert buf.level() == 0.0


def test_timestamp_is_set():
    buf = InputBuffer()
    buf.push("t")
    items = buf.consume(1)
    assert items[0]["timestamp_ms"] > 0

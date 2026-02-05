"""Tests for mavis.sheet_text."""

from mavis.sheet_text import SheetTextToken, parse, text_to_chars


def test_plain_text():
    chars = text_to_chars("hello world")
    tokens = parse(chars)
    assert len(tokens) == 2
    assert tokens[0].text == "hello"
    assert tokens[0].emphasis == "none"
    assert tokens[1].text == "world"


def test_loud_emphasis():
    chars = text_to_chars("the SUN rises")
    tokens = parse(chars)
    assert len(tokens) == 3
    assert tokens[0].emphasis == "none"
    assert tokens[1].text == "SUN"
    assert tokens[1].emphasis == "loud"
    assert tokens[2].emphasis == "none"


def test_shout_emphasis():
    chars = text_to_chars("I SAID STOP")
    tokens = parse(chars)
    # All three words are uppercase in a row -> all promoted to "shout"
    assert tokens[0].emphasis == "shout"
    assert tokens[1].text == "SAID"
    assert tokens[1].emphasis == "shout"
    assert tokens[2].text == "STOP"
    assert tokens[2].emphasis == "shout"


def test_soft_emphasis():
    chars = text_to_chars("falling _gently_")
    tokens = parse(chars)
    assert len(tokens) == 2
    assert tokens[0].emphasis == "none"
    assert tokens[1].text == "gently"
    assert tokens[1].emphasis == "soft"


def test_sustain():
    chars = text_to_chars("hold... this")
    tokens = parse(chars)
    assert tokens[0].text == "hold"
    assert tokens[0].sustain is True
    assert tokens[0].duration_modifier == 2.0
    assert tokens[1].sustain is False


def test_harmony_brackets():
    chars = text_to_chars("singing [together]")
    tokens = parse(chars)
    assert len(tokens) == 2
    assert tokens[1].text == "together"
    assert tokens[1].harmony is True


def test_harmony_ctrl():
    chars = [
        {"char": "h", "shift": False, "ctrl": True, "alt": False, "timestamp_ms": 0},
        {"char": "i", "shift": False, "ctrl": True, "alt": False, "timestamp_ms": 0},
    ]
    tokens = parse(chars)
    assert tokens[0].harmony is True


def test_mixed_markup():
    chars = text_to_chars("the SUN... is falling _down_")
    tokens = parse(chars)
    assert len(tokens) == 5
    assert tokens[0].text == "the"
    assert tokens[0].emphasis == "none"
    # SUN... -> loud + sustain
    assert tokens[1].text == "SUN"
    assert tokens[1].emphasis == "loud"
    assert tokens[1].sustain is True
    assert tokens[2].text == "is"
    assert tokens[2].emphasis == "none"
    assert tokens[3].text == "falling"
    assert tokens[3].emphasis == "none"
    # "_down_" -> soft
    assert tokens[4].text == "down"
    assert tokens[4].emphasis == "soft"


def test_empty_input():
    tokens = parse([])
    assert tokens == []


def test_standalone_ellipsis():
    chars = text_to_chars("...")
    tokens = parse(chars)
    assert len(tokens) == 1
    assert tokens[0].sustain is True
    assert tokens[0].text == "..."


def test_text_to_chars_shift_detection():
    chars = text_to_chars("aB")
    assert chars[0]["shift"] is False
    assert chars[1]["shift"] is True

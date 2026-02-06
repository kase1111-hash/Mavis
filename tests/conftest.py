"""Shared test fixtures and helpers for Mavis test suite."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from mavis.llm_processor import PhonemeEvent
from mavis.sheet_text import SheetTextToken


# --- Date Helpers ---


def future_date(days=365):
    """Return an ISO-format date in the future."""
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def past_date(days=30):
    """Return an ISO-format date in the past."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# --- Factory Helpers ---


def make_phoneme_event(
    phoneme="AH",
    volume=0.5,
    pitch_hz=220.0,
    duration_ms=100,
    vibrato=False,
    breathiness=0.0,
):
    """Create a PhonemeEvent with sensible defaults."""
    return PhonemeEvent(
        phoneme=phoneme,
        start_ms=0,
        duration_ms=duration_ms,
        volume=volume,
        pitch_hz=pitch_hz,
        vibrato=vibrato,
        breathiness=breathiness,
        harmony_intervals=[],
    )


def make_token(text="hello", emphasis="none", sustain=False, harmony=False):
    """Create a SheetTextToken with sensible defaults."""
    return SheetTextToken(
        text=text,
        emphasis=emphasis,
        sustain=sustain,
        harmony=harmony,
        duration_modifier=1.0,
    )


# --- Fixtures ---


@pytest.fixture
def tmp_json_path():
    """Provide a temporary JSON file path, cleaned up after use."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory, cleaned up after use."""
    d = tempfile.mkdtemp()
    yield d
    import shutil
    shutil.rmtree(d, ignore_errors=True)

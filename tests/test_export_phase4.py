"""Tests for Phase 4 additions to mavis.export -- JSONL, audio gen, IML validation."""

import os
import tempfile

from mavis.export import (
    PerformanceRecording,
    export_dataset_jsonl,
    generate_audio_for_recording,
    tokens_to_iml,
    validate_iml,
)
from mavis.llm_processor import PhonemeEvent
from mavis.sheet_text import SheetTextToken


def _make_phoneme(phoneme="AH", volume=0.5, pitch_hz=220.0, duration_ms=100):
    return PhonemeEvent(
        phoneme=phoneme, start_ms=0, duration_ms=duration_ms,
        volume=volume, pitch_hz=pitch_hz, vibrato=False,
        breathiness=0.0, harmony_intervals=[],
    )


def _make_recording(consent=True):
    rec = PerformanceRecording(song_id="test", transcript="hello world")
    rec.phoneme_events = [
        _make_phoneme("HH", 0.5, 220.0),
        _make_phoneme("EH", 0.6, 230.0),
        _make_phoneme("L", 0.5, 220.0),
    ]
    rec.consent = consent
    rec.score = 100
    rec.grade = "B"
    return rec


# --- JSONL Export ---

def test_export_jsonl_basic():
    rec = _make_recording(consent=True)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        count = export_dataset_jsonl([rec], path)
        assert count == 1
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 1
        import json
        entry = json.loads(lines[0])
        assert entry["source"] == "mavis"
    finally:
        os.unlink(path)


def test_export_jsonl_skips_no_consent():
    rec_consent = _make_recording(consent=True)
    rec_no_consent = _make_recording(consent=False)
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        count = export_dataset_jsonl([rec_consent, rec_no_consent], path)
        assert count == 1
    finally:
        os.unlink(path)


def test_export_jsonl_empty():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        count = export_dataset_jsonl([], path)
        assert count == 0
    finally:
        os.unlink(path)


def test_export_jsonl_multiple():
    recs = [_make_recording(consent=True) for _ in range(5)]
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        path = f.name
    try:
        count = export_dataset_jsonl(recs, path)
        assert count == 5
        with open(path) as f:
            lines = f.readlines()
        assert len(lines) == 5
    finally:
        os.unlink(path)


# --- Audio Generation ---

def test_generate_audio_creates_wav():
    rec = _make_recording()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        result = generate_audio_for_recording(rec, path)
        assert result == path
        assert os.path.isfile(path)
        # Check WAV header
        with open(path, "rb") as f:
            header = f.read(4)
        assert header == b"RIFF"
    finally:
        os.unlink(path)


def test_generate_audio_nonzero_size():
    rec = _make_recording()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        generate_audio_for_recording(rec, path)
        assert os.path.getsize(path) > 44  # More than just header
    finally:
        os.unlink(path)


def test_generate_audio_empty_recording():
    rec = PerformanceRecording()
    rec.phoneme_events = []
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        generate_audio_for_recording(rec, path)
        assert os.path.isfile(path)
        # Should still have a valid WAV header (44 bytes)
        assert os.path.getsize(path) == 44
    finally:
        os.unlink(path)


# --- IML Validation ---

def test_validate_iml_valid():
    tokens = [
        SheetTextToken(text="SUN", emphasis="loud"),
        SheetTextToken(text="rise", emphasis="none"),
    ]
    iml = tokens_to_iml(tokens)
    errors = validate_iml(iml)
    assert errors == []


def test_validate_iml_missing_root():
    errors = validate_iml("just plain text")
    assert len(errors) > 0
    assert any("root" in e.lower() or "iml" in e.lower() for e in errors)


def test_validate_iml_missing_closing():
    errors = validate_iml('<iml version="1.0.0"><utterance>')
    assert len(errors) > 0


def test_validate_iml_missing_version():
    iml = "<iml><utterance></utterance></iml>"
    errors = validate_iml(iml)
    assert any("version" in e.lower() for e in errors)


def test_validate_iml_unmatched_tags():
    iml = '<iml version="1.0.0"><utterance><prosody volume="+6dB">test</utterance></iml>'
    errors = validate_iml(iml)
    assert any("prosody" in e.lower() for e in errors)

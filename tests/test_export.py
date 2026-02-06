"""Tests for mavis.export -- Prosody-Protocol integration."""

import json
import os
import tempfile

from mavis.export import (
    PerformanceRecording,
    extract_training_features,
    export_dataset,
    export_performance,
    infer_emotion,
    phoneme_events_to_iml,
    recording_to_dataset_entry,
    tokens_to_iml,
)
from mavis.llm_processor import PhonemeEvent
from mavis.output_buffer import BufferState
from mavis.sheet_text import SheetTextToken


def _make_events():
    """Helper: create a small list of PhonemeEvents."""
    return [
        PhonemeEvent(phoneme="s", start_ms=0, duration_ms=100, volume=0.5,
                     pitch_hz=220.0),
        PhonemeEvent(phoneme="ah", start_ms=100, duration_ms=200, volume=0.8,
                     pitch_hz=264.0, vibrato=True),
        PhonemeEvent(phoneme="n", start_ms=300, duration_ms=100, volume=0.5,
                     pitch_hz=220.0),
    ]


def _make_tokens():
    """Helper: create a small list of SheetTextTokens."""
    return [
        SheetTextToken(text="the", emphasis="none"),
        SheetTextToken(text="SUN", emphasis="loud", sustain=True, duration_modifier=2.0),
        SheetTextToken(text="rises", emphasis="none"),
    ]


# --- IML generation ---

def test_tokens_to_iml_valid_xml():
    tokens = _make_tokens()
    iml = tokens_to_iml(tokens)
    assert iml.startswith('<iml version="1.0.0"')
    assert "</iml>" in iml
    assert "<utterance" in iml
    assert "</utterance>" in iml


def test_tokens_to_iml_prosody_tags():
    tokens = _make_tokens()
    iml = tokens_to_iml(tokens)
    # "SUN" is loud -> should have <prosody> tag
    assert "<prosody" in iml
    assert 'volume="+6dB"' in iml


def test_tokens_to_iml_emphasis_tags():
    tokens = _make_tokens()
    iml = tokens_to_iml(tokens)
    # "SUN" is loud -> emphasis level "moderate"
    assert '<emphasis level="moderate">' in iml


def test_tokens_to_iml_pause_for_sustain():
    tokens = _make_tokens()
    iml = tokens_to_iml(tokens)
    # SUN has sustain -> should have <pause> tag
    assert "<pause" in iml
    assert 'duration="' in iml


def test_tokens_to_iml_soft():
    tokens = [SheetTextToken(text="gently", emphasis="soft")]
    iml = tokens_to_iml(tokens)
    assert 'quality="breathy"' in iml
    assert 'volume="-6dB"' in iml


def test_tokens_to_iml_shout():
    tokens = [SheetTextToken(text="STOP", emphasis="shout")]
    iml = tokens_to_iml(tokens)
    assert 'volume="+12dB"' in iml
    assert 'quality="tense"' in iml
    assert '<emphasis level="strong">' in iml


def test_phoneme_events_to_iml():
    events = _make_events()
    iml = phoneme_events_to_iml(events, transcript="SUN")
    assert '<iml version="1.0.0"' in iml
    assert "</iml>" in iml
    assert "<utterance" in iml


def test_phoneme_events_to_iml_empty():
    iml = phoneme_events_to_iml([])
    assert "<iml" in iml


# --- Emotion inference ---

def test_infer_emotion_neutral():
    events = [PhonemeEvent(phoneme="ah", volume=0.5, pitch_hz=220.0)]
    assert infer_emotion(events) == "neutral"


def test_infer_emotion_angry():
    events = [PhonemeEvent(phoneme="ah", volume=0.9, pitch_hz=300.0)]
    assert infer_emotion(events) == "angry"


def test_infer_emotion_joyful():
    events = [PhonemeEvent(phoneme="ah", volume=0.9, pitch_hz=180.0)]
    assert infer_emotion(events) == "joyful"


def test_infer_emotion_sad():
    events = [PhonemeEvent(phoneme="ah", volume=0.5, pitch_hz=220.0, breathiness=0.8)]
    assert infer_emotion(events) == "sad"


def test_infer_emotion_calm():
    events = [PhonemeEvent(phoneme="ah", volume=0.2, pitch_hz=220.0)]
    assert infer_emotion(events) == "calm"


def test_infer_emotion_empty():
    assert infer_emotion([]) == "neutral"


# --- Training features ---

def test_extract_training_features():
    events = _make_events()
    features = extract_training_features(events)
    assert len(features) == 7
    assert features[0] > 0  # mean_pitch_hz > 0
    assert features[2] > 0  # mean_volume > 0
    assert 0.0 <= features[6] <= 1.0  # vibrato_ratio in [0, 1]


def test_extract_training_features_empty():
    features = extract_training_features([])
    assert features == [0.0] * 7


def test_extract_training_features_vibrato_ratio():
    events = [
        PhonemeEvent(phoneme="ah", duration_ms=100, vibrato=True),
        PhonemeEvent(phoneme="ah", duration_ms=100, vibrato=False),
    ]
    features = extract_training_features(events)
    assert features[6] == 0.5  # 1 out of 2 has vibrato


# --- PerformanceRecording ---

def test_recording_events():
    rec = PerformanceRecording()
    assert len(rec.events) == 0

    rec.record_keystroke(0, "a", {"shift": False})
    assert len(rec.events) == 1
    assert rec.events[0].event_type == "keystroke"

    tok = SheetTextToken(text="hello")
    rec.record_token(10, tok)
    assert len(rec.events) == 2
    assert len(rec.tokens) == 1

    ev = PhonemeEvent(phoneme="hh", duration_ms=100)
    rec.record_phoneme(20, ev)
    assert len(rec.events) == 3
    assert len(rec.phoneme_events) == 1

    buf = BufferState(level=0.5, status="optimal", drain_rate=1.0, fill_rate=2.0)
    rec.record_buffer_state(30, buf)
    assert len(rec.events) == 4


# --- Dataset entry ---

def test_recording_to_dataset_entry():
    rec = PerformanceRecording(
        transcript="the SUN rises",
        consent=True,
        score=500,
        grade="B",
    )
    for ev in _make_events():
        rec.record_phoneme(0, ev)
    for tok in _make_tokens():
        rec.record_token(0, tok)

    entry = recording_to_dataset_entry(rec)

    # Required fields per dataset-entry.schema.json
    assert entry["source"] == "mavis"
    assert entry["consent"] is True
    assert entry["annotator"] == "model"
    assert entry["language"] == "en-US"
    assert entry["transcript"] == "the SUN rises"
    assert "<iml" in entry["iml"]
    assert entry["emotion_label"] in (
        "neutral", "angry", "joyful", "sad", "calm",
        "sincere", "sarcastic", "frustrated", "uncertain",
        "fearful", "surprised", "disgusted", "empathetic",
    )
    assert entry["id"].startswith("mavis_")
    assert entry["metadata"]["score"] == 500
    assert entry["metadata"]["grade"] == "B"


# --- File export ---

def test_export_performance_writes_json():
    rec = PerformanceRecording(transcript="test", consent=True)
    ev = PhonemeEvent(phoneme="t", duration_ms=100)
    rec.record_phoneme(0, ev)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_entry.json")
        export_performance(rec, path)

        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data["source"] == "mavis"
        assert "<iml" in data["iml"]


def test_export_dataset_creates_directory():
    rec1 = PerformanceRecording(transcript="one", consent=True)
    rec1.record_phoneme(0, PhonemeEvent(phoneme="w", duration_ms=100))
    rec2 = PerformanceRecording(transcript="two", consent=True)
    rec2.record_phoneme(0, PhonemeEvent(phoneme="t", duration_ms=100))

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, "corpus")
        export_dataset([rec1, rec2], out)

        assert os.path.isfile(os.path.join(out, "metadata.json"))
        assert os.path.isfile(os.path.join(out, "entries", "mavis_session_001.json"))
        assert os.path.isfile(os.path.join(out, "entries", "mavis_session_002.json"))

        with open(os.path.join(out, "metadata.json")) as f:
            meta = json.load(f)
        assert meta["size"] == 2
        assert meta["source"] == "mavis"


# --- Pipeline recording integration ---

def test_pipeline_recording():
    from mavis.config import MavisConfig
    from mavis.pipeline import create_pipeline

    config = MavisConfig()
    pipe = create_pipeline(config)
    rec = pipe.start_recording(song_id="twinkle")

    assert pipe.recording is rec
    assert rec.song_id == "twinkle"

    pipe.feed_text("hello")
    pipe.tick()
    pipe.tick()

    result = pipe.stop_recording()
    assert result is rec
    assert pipe.recording is None
    assert len(rec.events) > 0
    # Should have keystrokes from feed_text
    keystroke_events = [e for e in rec.events if e.event_type == "keystroke"]
    assert len(keystroke_events) == 5  # "hello" = 5 chars

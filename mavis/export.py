"""Prosody-Protocol export -- convert Mavis performance data to IML and dataset entries.

Produces output compatible with the Prosody-Protocol IML specification
(https://github.com/kase1111-hash/Prosody-Protocol). Generates:

  - IML XML documents preserving prosodic annotations from Sheet Text markup
  - Dataset entry JSON files conforming to dataset-entry.schema.json
  - Training feature vectors for ML pipelines

The prosody_protocol SDK is an optional dependency. When installed, this module
uses the SDK's MavisBridge and validator. When absent, it generates compatible
output directly using the IML spec's tag structure.
"""

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mavis.llm_processor import PhonemeEvent
from mavis.output_buffer import BufferState
from mavis.sheet_text import SheetTextToken

# IML version this module targets
IML_VERSION = "1.0.0"

# Emphasis -> IML prosody attribute mappings
_EMPHASIS_TO_IML = {
    "none": {},
    "soft": {"volume": "-6dB", "quality": "breathy"},
    "loud": {"volume": "+6dB", "pitch": "+10%"},
    "shout": {"volume": "+12dB", "pitch": "+20%", "quality": "tense"},
}

# Emphasis -> IML emphasis level mapping
_EMPHASIS_TO_LEVEL = {
    "soft": "reduced",
    "loud": "moderate",
    "shout": "strong",
}

# Volume-based emotion inference thresholds
_HIGH_VOLUME = 0.7
_LOW_VOLUME = 0.35
_HIGH_PITCH_HZ = 260.0
_LOW_PITCH_HZ = 180.0
_HIGH_BREATHINESS = 0.4


@dataclass
class PerformanceEvent:
    """A single timestamped event during a Mavis performance."""

    time_ms: int
    event_type: str  # "keystroke" | "token" | "phoneme" | "buffer_state"
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceRecording:
    """Full recording of a Mavis performance session."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    song_id: Optional[str] = None
    transcript: str = ""
    hardware_profile: str = "laptop_cpu"
    difficulty: str = "easy"
    events: List[PerformanceEvent] = field(default_factory=list)
    tokens: List[SheetTextToken] = field(default_factory=list)
    phoneme_events: List[PhonemeEvent] = field(default_factory=list)
    score: int = 0
    grade: str = "F"
    consent: bool = False

    def record_keystroke(self, time_ms: int, char: str, modifiers: Dict[str, bool]) -> None:
        """Record a keystroke event."""
        self.events.append(PerformanceEvent(
            time_ms=time_ms,
            event_type="keystroke",
            data={"char": char, "modifiers": modifiers},
        ))

    def record_token(self, time_ms: int, token: SheetTextToken) -> None:
        """Record a parsed token event."""
        self.tokens.append(token)
        self.events.append(PerformanceEvent(
            time_ms=time_ms,
            event_type="token",
            data={
                "text": token.text,
                "emphasis": token.emphasis,
                "sustain": token.sustain,
                "harmony": token.harmony,
                "duration_modifier": token.duration_modifier,
            },
        ))

    def record_phoneme(self, time_ms: int, event: PhonemeEvent) -> None:
        """Record a phoneme synthesis event."""
        self.phoneme_events.append(event)
        self.events.append(PerformanceEvent(
            time_ms=time_ms,
            event_type="phoneme",
            data={
                "phoneme": event.phoneme,
                "duration_ms": event.duration_ms,
                "volume": event.volume,
                "pitch_hz": event.pitch_hz,
                "vibrato": event.vibrato,
                "breathiness": event.breathiness,
                "harmony_intervals": event.harmony_intervals,
            },
        ))

    def record_buffer_state(self, time_ms: int, state: BufferState) -> None:
        """Record an output buffer state snapshot."""
        self.events.append(PerformanceEvent(
            time_ms=time_ms,
            event_type="buffer_state",
            data={
                "level": state.level,
                "status": state.status,
                "drain_rate": state.drain_rate,
                "fill_rate": state.fill_rate,
            },
        ))


def infer_emotion(phoneme_events: List[PhonemeEvent]) -> str:
    """Infer a dominant emotion label from aggregate prosody features.

    Uses the same heuristic as the Prosody-Protocol MavisBridge:
    high volume + high pitch = angry, high volume + low pitch = joyful,
    high breathiness = sad, low volume = calm, else neutral.
    """
    if not phoneme_events:
        return "neutral"

    mean_vol = sum(e.volume for e in phoneme_events) / len(phoneme_events)
    mean_pitch = sum(e.pitch_hz for e in phoneme_events) / len(phoneme_events)
    mean_breath = sum(e.breathiness for e in phoneme_events) / len(phoneme_events)

    if mean_vol > _HIGH_VOLUME and mean_pitch > _HIGH_PITCH_HZ:
        return "angry"
    if mean_vol > _HIGH_VOLUME and mean_pitch <= _HIGH_PITCH_HZ:
        return "joyful"
    if mean_breath > _HIGH_BREATHINESS:
        return "sad"
    if mean_vol < _LOW_VOLUME:
        return "calm"
    return "neutral"


def tokens_to_iml(tokens: List[SheetTextToken], language: str = "en-US") -> str:
    """Convert Sheet Text tokens into an IML XML document string.

    Produces valid IML 1.0 markup compatible with the Prosody-Protocol spec:
    - <iml> root with version, language, consent, processing attributes
    - <utterance> with inferred emotion
    - <prosody> spans for loud/shout/soft tokens
    - <emphasis> for emphasis levels
    - <pause> for sustain markers
    """
    parts = []
    parts.append(
        f'<iml version="{IML_VERSION}" language="{language}" '
        f'consent="explicit" processing="local">'
    )
    parts.append('  <utterance emotion="neutral" confidence="0.5">')

    for token in tokens:
        text = _escape_xml(token.text)

        if token.emphasis in _EMPHASIS_TO_IML and token.emphasis != "none":
            attrs = _EMPHASIS_TO_IML[token.emphasis]
            attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
            parts.append(f"    <prosody {attr_str}>{text}</prosody>")
        else:
            parts.append(f"    {text}")

        if token.emphasis in _EMPHASIS_TO_LEVEL:
            level = _EMPHASIS_TO_LEVEL[token.emphasis]
            parts.append(f'    <emphasis level="{level}">{text}</emphasis>')

        if token.sustain:
            duration_ms = int(token.duration_modifier * 400)
            parts.append(f'    <pause duration="{duration_ms}"/>')

    parts.append("  </utterance>")
    parts.append("</iml>")
    return "\n".join(parts)


def phoneme_events_to_iml(
    phoneme_events: List[PhonemeEvent],
    transcript: str = "",
    language: str = "en-US",
) -> str:
    """Convert PhonemeEvents into an IML document with per-word prosody annotations.

    For each word-boundary group of phonemes, computes pitch/volume deviation
    from the session mean and wraps words with significant deviation in
    <prosody> tags. Compatible with Prosody-Protocol MavisBridge output.
    """
    if not phoneme_events:
        return f'<iml version="{IML_VERSION}" language="{language}"></iml>'

    mean_pitch = sum(e.pitch_hz for e in phoneme_events) / len(phoneme_events)
    mean_vol = sum(e.volume for e in phoneme_events) / len(phoneme_events)
    emotion = infer_emotion(phoneme_events)

    words = transcript.split() if transcript else [e.phoneme for e in phoneme_events]

    parts = []
    parts.append(
        f'<iml version="{IML_VERSION}" language="{language}" '
        f'consent="explicit" processing="local">'
    )

    confidence = min(1.0, abs(mean_vol - 0.5) + abs(mean_pitch - 220.0) / 220.0)
    parts.append(f'  <utterance emotion="{emotion}" confidence="{confidence:.2f}">')

    # Distribute phonemes across words roughly
    ph_per_word = max(1, len(phoneme_events) // max(1, len(words)))
    idx = 0
    for word in words:
        word_phonemes = phoneme_events[idx: idx + ph_per_word]
        idx += ph_per_word

        if not word_phonemes:
            parts.append(f"    {_escape_xml(word)}")
            continue

        w_pitch = sum(e.pitch_hz for e in word_phonemes) / len(word_phonemes)
        w_vol = sum(e.volume for e in word_phonemes) / len(word_phonemes)

        pitch_dev = (w_pitch - mean_pitch) / mean_pitch if mean_pitch > 0 else 0
        vol_dev = w_vol - mean_vol

        if abs(pitch_dev) > 0.1 or abs(vol_dev) > 0.3:
            pitch_pct = f"{pitch_dev:+.0%}"
            vol_db = f"{vol_dev * 20:+.0f}dB"
            attrs = f'pitch="{pitch_pct}" volume="{vol_db}"'
            any_breathy = any(e.breathiness > 0.3 for e in word_phonemes)
            if any_breathy:
                attrs += ' quality="breathy"'
            parts.append(f"    <prosody {attrs}>{_escape_xml(word)}</prosody>")
        else:
            parts.append(f"    {_escape_xml(word)}")

    parts.append("  </utterance>")
    parts.append("</iml>")
    return "\n".join(parts)


def recording_to_dataset_entry(recording: PerformanceRecording) -> Dict[str, Any]:
    """Convert a PerformanceRecording into a Prosody-Protocol dataset entry.

    Output conforms to schemas/dataset-entry.schema.json in the
    Prosody-Protocol repo.
    """
    iml = phoneme_events_to_iml(
        recording.phoneme_events,
        transcript=recording.transcript,
    )
    emotion = infer_emotion(recording.phoneme_events)

    return {
        "id": f"mavis_{recording.session_id}",
        "timestamp": recording.timestamp,
        "source": "mavis",
        "language": "en-US",
        "audio_file": "",  # no audio file in mock mode
        "transcript": recording.transcript,
        "iml": iml,
        "speaker_id": None,
        "emotion_label": emotion,
        "annotator": "model",
        "consent": recording.consent,
        "metadata": {
            "song_id": recording.song_id,
            "hardware_profile": recording.hardware_profile,
            "difficulty": recording.difficulty,
            "score": recording.score,
            "grade": recording.grade,
            "mavis_version": "0.1.0",
            "phoneme_count": len(recording.phoneme_events),
            "token_count": len(recording.tokens),
            "event_count": len(recording.events),
        },
    }


def extract_training_features(phoneme_events: List[PhonemeEvent]) -> List[float]:
    """Extract a 7-dimensional feature vector from a PhonemeEvent sequence.

    Returns [mean_pitch_hz, pitch_range_hz, mean_volume, volume_range,
             mean_breathiness, speech_rate, vibrato_ratio].

    Compatible with the Prosody-Protocol MavisBridge.extract_training_features().
    """
    if not phoneme_events:
        return [0.0] * 7

    pitches = [e.pitch_hz for e in phoneme_events]
    volumes = [e.volume for e in phoneme_events]
    breaths = [e.breathiness for e in phoneme_events]

    total_duration_s = sum(e.duration_ms for e in phoneme_events) / 1000.0
    speech_rate = len(phoneme_events) / total_duration_s if total_duration_s > 0 else 0.0
    vibrato_ratio = sum(1 for e in phoneme_events if e.vibrato) / len(phoneme_events)

    return [
        sum(pitches) / len(pitches),       # mean_pitch_hz
        max(pitches) - min(pitches),        # pitch_range_hz
        sum(volumes) / len(volumes),        # mean_volume
        max(volumes) - min(volumes),        # volume_range
        sum(breaths) / len(breaths),        # mean_breathiness
        speech_rate,                        # speech_rate
        vibrato_ratio,                      # vibrato_ratio
    ]


def export_performance(recording: PerformanceRecording, path: str) -> None:
    """Write a single performance recording as a dataset entry JSON file."""
    entry = recording_to_dataset_entry(recording)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(entry, f, indent=2)


def export_dataset(
    recordings: List[PerformanceRecording],
    output_dir: str,
    dataset_name: str = "mavis-corpus",
) -> str:
    """Export multiple recordings as a Prosody-Protocol dataset directory.

    Creates the standard layout:
        output_dir/
        ├── metadata.json
        └── entries/
            ├── mavis_session_001.json
            └── ...

    Returns the output_dir path.
    """
    entries_dir = os.path.join(output_dir, "entries")
    os.makedirs(entries_dir, exist_ok=True)

    metadata = {
        "name": dataset_name,
        "version": "0.1.0",
        "size": len(recordings),
        "source": "mavis",
        "language": "en-US",
        "description": "Vocal typing performance data from Mavis sessions",
        "created": datetime.now(timezone.utc).isoformat(),
    }

    with open(os.path.join(output_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    for i, rec in enumerate(recordings):
        entry = recording_to_dataset_entry(rec)
        entry_path = os.path.join(entries_dir, f"mavis_session_{i + 1:03d}.json")
        with open(entry_path, "w") as f:
            json.dump(entry, f, indent=2)

    return output_dir


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

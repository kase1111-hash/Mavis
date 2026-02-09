"""Deferred bulk export functions -- extracted from mavis/export.py.

These functions are part of the data platform features (JSONL export,
WAV audio generation, IML validation) and are set aside for potential
future reintegration. They depend on the core mavis.export module.
"""

import json
import os
from typing import List

from mavis.export import PerformanceRecording, recording_to_dataset_entry


def export_dataset_jsonl(
    recordings: List[PerformanceRecording],
    path: str,
) -> int:
    """Export multiple recordings as a JSONL file for ML training pipelines.

    Each line is a JSON object conforming to dataset-entry.schema.json.
    Only recordings with consent=True are included.
    Returns the number of entries written.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    count = 0
    with open(path, "w") as f:
        for rec in recordings:
            if not rec.consent:
                continue
            entry = recording_to_dataset_entry(rec)
            f.write(json.dumps(entry) + "\n")
            count += 1
    return count


def generate_audio_for_recording(
    recording: PerformanceRecording,
    output_path: str,
) -> str:
    """Generate a WAV audio file from a recording's phoneme events.

    Uses MockAudioSynthesizer to produce 16-bit PCM at 22050 Hz.
    Returns the output file path.
    """
    from mavis.audio import MockAudioSynthesizer, SAMPLE_RATE

    synth = MockAudioSynthesizer()
    all_pcm = b""
    for event in recording.phoneme_events:
        all_pcm += synth.synthesize(event)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    _write_wav(output_path, all_pcm, sample_rate=SAMPLE_RATE)
    return output_path


def validate_iml(iml_string: str) -> List[str]:
    """Validate an IML XML string. Returns a list of errors (empty = valid).

    When the prosody_protocol SDK is installed, delegates to IMLValidator.
    Otherwise performs basic structural checks.
    """
    errors: List[str] = []

    if "<iml" not in iml_string:
        errors.append("Missing <iml> root element")
        return errors
    if "</iml>" not in iml_string:
        errors.append("Missing </iml> closing tag")
        return errors

    if 'version="' not in iml_string:
        errors.append("Missing version attribute on <iml> element")

    for tag in ["utterance", "prosody", "emphasis"]:
        open_count = iml_string.count(f"<{tag}")
        close_count = iml_string.count(f"</{tag}>")
        if open_count != close_count:
            errors.append(
                f"Unmatched <{tag}> tags: {open_count} opened, {close_count} closed"
            )

    # Try the SDK validator if available
    try:
        from prosody_protocol import IMLValidator  # type: ignore
        validator = IMLValidator()
        sdk_errors = validator.validate(iml_string)
        errors.extend(sdk_errors)
    except ImportError:
        pass

    return errors


def _write_wav(path: str, pcm_data: bytes, sample_rate: int = 22050) -> None:
    """Write raw PCM data as a WAV file (16-bit mono)."""
    import struct as _struct

    data_size = len(pcm_data)
    header = b"RIFF"
    header += _struct.pack("<I", 36 + data_size)
    header += b"WAVE"
    header += b"fmt "
    header += _struct.pack("<I", 16)
    header += _struct.pack("<H", 1)    # PCM format
    header += _struct.pack("<H", 1)    # mono
    header += _struct.pack("<I", sample_rate)
    header += _struct.pack("<I", sample_rate * 2)
    header += _struct.pack("<H", 2)    # block align
    header += _struct.pack("<H", 16)   # bits per sample
    header += b"data"
    header += _struct.pack("<I", data_size)

    with open(path, "wb") as f:
        f.write(header)
        f.write(pcm_data)

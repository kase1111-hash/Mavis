"""Tests for mavis.audio."""

import shutil
import struct

import pytest

from mavis.audio import (
    _ARPABET_TO_KIRSHENBAUM,
    SAMPLE_RATE,
    SAMPLE_WIDTH,
    EspeakSynthesizer,
    MockAudioSynthesizer,
)
from mavis.llm_processor import PhonemeEvent


def test_correct_byte_length():
    synth = MockAudioSynthesizer()
    event = PhonemeEvent(phoneme="ah", duration_ms=100, volume=0.5, pitch_hz=220.0)
    data = synth.synthesize(event)
    expected_samples = int(SAMPLE_RATE * 100 / 1000)
    expected_bytes = expected_samples * SAMPLE_WIDTH
    assert len(data) == expected_bytes


def test_zero_volume_silence():
    synth = MockAudioSynthesizer()
    event = PhonemeEvent(phoneme="ah", duration_ms=50, volume=0.0, pitch_hz=220.0)
    data = synth.synthesize(event)
    # All bytes should be zero (silence)
    assert all(b == 0 for b in data)


def test_nonzero_volume_produces_sound():
    synth = MockAudioSynthesizer()
    event = PhonemeEvent(phoneme="ah", duration_ms=50, volume=1.0, pitch_hz=220.0)
    data = synth.synthesize(event)
    assert any(b != 0 for b in data)


def test_vibrato_changes_output():
    synth = MockAudioSynthesizer()
    base = PhonemeEvent(phoneme="ah", duration_ms=100, volume=0.5, pitch_hz=220.0,
                        vibrato=False)
    vib = PhonemeEvent(phoneme="ah", duration_ms=100, volume=0.5, pitch_hz=220.0,
                       vibrato=True)
    data_base = synth.synthesize(base)
    data_vib = synth.synthesize(vib)
    assert data_base != data_vib


def test_harmony_changes_output():
    synth = MockAudioSynthesizer()
    base = PhonemeEvent(phoneme="ah", duration_ms=100, volume=0.5, pitch_hz=220.0)
    harm = PhonemeEvent(phoneme="ah", duration_ms=100, volume=0.5, pitch_hz=220.0,
                        harmony_intervals=[4, 7])
    data_base = synth.synthesize(base)
    data_harm = synth.synthesize(harm)
    assert data_base != data_harm


def test_zero_duration():
    synth = MockAudioSynthesizer()
    event = PhonemeEvent(phoneme="ah", duration_ms=0, volume=0.5, pitch_hz=220.0)
    data = synth.synthesize(event)
    assert data == b""


def test_play_no_error():
    synth = MockAudioSynthesizer()
    synth.play(b"\x00\x00")  # should not raise


# --- EspeakSynthesizer ---

_HAS_ESPEAK = shutil.which("espeak-ng") is not None
requires_espeak = pytest.mark.skipif(not _HAS_ESPEAK, reason="espeak-ng not installed")


def test_espeak_missing_binary_raises(monkeypatch):
    monkeypatch.setattr("mavis.audio.shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="espeak-ng"):
        EspeakSynthesizer()


def test_all_mock_llm_phonemes_have_mappings():
    """Every phoneme MockLLMProcessor can emit must map to Kirshenbaum."""
    from mavis.llm_processor import _WORD_PHONEMES
    dictionary = {p for phonemes in _WORD_PHONEMES.values() for p in phonemes}
    fallback = set("abcdefghijklmnopqrstuvwxyz")  # letter-by-letter path
    missing = (dictionary | fallback) - set(_ARPABET_TO_KIRSHENBAUM)
    assert not missing, f"unmapped phonemes: {sorted(missing)}"


@requires_espeak
def test_espeak_correct_byte_length():
    synth = EspeakSynthesizer()
    event = PhonemeEvent(phoneme="aa", duration_ms=100, volume=0.8, pitch_hz=220.0)
    data = synth.synthesize(event)
    assert len(data) == int(SAMPLE_RATE * 100 / 1000) * SAMPLE_WIDTH


@requires_espeak
def test_espeak_produces_sound_for_all_phonemes():
    synth = EspeakSynthesizer()
    for phoneme in sorted(_ARPABET_TO_KIRSHENBAUM):
        event = PhonemeEvent(phoneme=phoneme, duration_ms=150, volume=0.8,
                             pitch_hz=220.0)
        data = synth.synthesize(event)
        count = len(data) // 2
        peak = max(abs(s) for s in struct.unpack(f"<{count}h", data))
        assert peak > 300, f"phoneme {phoneme!r} is silent (peak={peak})"


@requires_espeak
def test_espeak_unmapped_phoneme_is_silence():
    synth = EspeakSynthesizer()
    event = PhonemeEvent(phoneme="42", duration_ms=100, volume=0.8, pitch_hz=220.0)
    data = synth.synthesize(event)
    assert len(data) == int(SAMPLE_RATE * 100 / 1000) * SAMPLE_WIDTH
    assert all(b == 0 for b in data)


@requires_espeak
def test_espeak_pitch_tracks_target():
    """Synthesized vowel F0 must be within 6% of the requested pitch."""
    synth = EspeakSynthesizer()

    def measure_f0(data):
        count = len(data) // 2
        samples = list(struct.unpack(f"<{count}h", data))
        mid = samples[count // 4: 3 * count // 4]
        best_lag, best_corr = 0, 0.0
        for lag in range(SAMPLE_RATE // 600, SAMPLE_RATE // 60):
            c = sum(mid[i] * mid[i + lag] for i in range(0, len(mid) - lag, 2))
            if c > best_corr:
                best_corr, best_lag = c, lag
        return SAMPLE_RATE / best_lag if best_lag else 0

    for target in [165.0, 220.0, 330.0]:
        event = PhonemeEvent(phoneme="aa", duration_ms=400, volume=0.8,
                             pitch_hz=target)
        got = measure_f0(synth.synthesize(event))
        assert abs(got - target) / target < 0.06, (
            f"target {target}Hz, got {got:.0f}Hz"
        )


@requires_espeak
def test_espeak_sustain_loops_to_duration():
    """A long note must be sustained, not padded with silence."""
    synth = EspeakSynthesizer()
    event = PhonemeEvent(phoneme="ow", duration_ms=2000, volume=0.8,
                         pitch_hz=220.0, vibrato=True)
    data = synth.synthesize(event)
    count = len(data) // 2
    assert count == SAMPLE_RATE * 2
    samples = struct.unpack(f"<{count}h", data)
    # The last quarter (excluding the fade-out tail) must still be voiced
    tail = samples[3 * count // 4: count - SAMPLE_RATE // 100]
    assert max(abs(s) for s in tail) > 300


@requires_espeak
def test_espeak_prosody_features_change_output():
    synth = EspeakSynthesizer()
    base = PhonemeEvent(phoneme="ow", duration_ms=200, volume=0.8, pitch_hz=220.0)
    for kwargs in [{"vibrato": True}, {"breathiness": 0.6},
                   {"harmony_intervals": [4, 7]}, {"volume": 0.3}]:
        variant = PhonemeEvent(phoneme="ow", duration_ms=200, pitch_hz=220.0,
                               volume=kwargs.pop("volume", 0.8), **kwargs)
        assert synth.synthesize(base) != synth.synthesize(variant)


@requires_espeak
def test_espeak_pipeline_integration():
    from mavis.config import MavisConfig
    from mavis.pipeline import create_pipeline

    pipe = create_pipeline(MavisConfig(tts_backend="espeak"))
    pipe.feed_text("twinkle twinkle little star ")
    for _ in range(5):
        pipe.tick(elapsed_ms=0)
    pipe.tick(elapsed_ms=1000)
    audio = pipe.take_audio()
    assert len(audio) > 0
    count = len(audio) // 2
    peak = max(abs(s) for s in struct.unpack(f"<{count}h", audio))
    assert peak > 300

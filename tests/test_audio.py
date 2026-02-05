"""Tests for mavis.audio."""

from mavis.audio import SAMPLE_RATE, SAMPLE_WIDTH, MockAudioSynthesizer
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

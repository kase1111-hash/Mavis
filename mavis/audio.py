"""Audio synthesis -- converts PhonemeEvents into audio waveform data."""

import abc
import math
import struct
from typing import List

from mavis.llm_processor import PhonemeEvent

SAMPLE_RATE = 22050
SAMPLE_WIDTH = 2  # 16-bit


class AudioSynthesizer(abc.ABC):
    """Abstract base class for audio synthesis backends."""

    @abc.abstractmethod
    def synthesize(self, event: PhonemeEvent) -> bytes:
        """Convert a PhonemeEvent into raw PCM audio bytes (16-bit, 22050 Hz)."""

    def play(self, audio_data: bytes) -> None:
        """Play audio data to speaker. Default is a no-op for testing."""


class MockAudioSynthesizer(AudioSynthesizer):
    """Generates sine-wave audio for testing purposes.

    Produces 16-bit PCM at 22050 Hz. Supports volume scaling,
    vibrato (pitch modulation), and harmony intervals.
    """

    def synthesize(self, event: PhonemeEvent) -> bytes:
        num_samples = int(SAMPLE_RATE * event.duration_ms / 1000)
        if num_samples == 0:
            return b""

        samples: List[int] = []
        for i in range(num_samples):
            t = i / SAMPLE_RATE

            # Base pitch with optional vibrato (5 Hz LFO, +-10 Hz)
            freq = event.pitch_hz
            if event.vibrato:
                freq += 10.0 * math.sin(2 * math.pi * 5.0 * t)

            # Generate sine wave for fundamental
            value = math.sin(2 * math.pi * freq * t)

            # Add harmony intervals (each interval is semitone offset)
            for interval in event.harmony_intervals:
                harmony_freq = freq * (2 ** (interval / 12.0))
                value += 0.5 * math.sin(2 * math.pi * harmony_freq * t)

            # Normalize if harmonies added
            if event.harmony_intervals:
                value /= 1.0 + 0.5 * len(event.harmony_intervals)

            # Apply volume
            value *= event.volume

            # Convert to 16-bit integer
            sample = int(value * 32767)
            sample = max(-32768, min(32767, sample))
            samples.append(sample)

        return struct.pack(f"<{len(samples)}h", *samples)

    def play(self, audio_data: bytes) -> None:
        """No-op for testing -- does not produce actual audio output."""
        pass


class EspeakSynthesizer(AudioSynthesizer):
    """Stub for espeak-ng integration via subprocess."""

    def synthesize(self, event: PhonemeEvent) -> bytes:
        raise NotImplementedError("espeak-ng integration pending")

    def play(self, audio_data: bytes) -> None:
        raise NotImplementedError("espeak-ng integration pending")


class CoquiSynthesizer(AudioSynthesizer):
    """Stub for Coqui TTS integration."""

    def synthesize(self, event: PhonemeEvent) -> bytes:
        raise NotImplementedError("Coqui TTS integration pending")

    def play(self, audio_data: bytes) -> None:
        raise NotImplementedError("Coqui TTS integration pending")

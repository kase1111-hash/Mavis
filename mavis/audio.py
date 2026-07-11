"""Audio synthesis -- converts PhonemeEvents into audio waveform data."""

import abc
import math
import shutil
import struct
import subprocess
from typing import Dict, List, Optional, Tuple

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


# ARPAbet-style phonemes (as produced by MockLLMProcessor) to espeak-ng's
# Kirshenbaum notation. Isolated stops and affricates render silent in
# espeak, so they carry a schwa to be realized -- you can't sing a bare "b".
_ARPABET_TO_KIRSHENBAUM = {
    # vowels
    "aa": "A:", "ae": "a", "ah": "V", "ao": "O:", "aw": "aU", "ax": "@",
    "ay": "aI", "eh": "E", "er": "3:", "ey": "eI", "ih": "I", "iy": "i:",
    "ow": "oU", "oy": "OI", "uh": "U", "uw": "u:",
    # consonants
    "b": "b@", "ch": "tS", "d": "d@", "dh": "D", "f": "f", "g": "g@",
    "hh": "h", "jh": "dZ@", "k": "k", "l": "l", "m": "m", "n": "n",
    "ng": "N", "p": "p", "r": "r@", "s": "s", "sh": "S", "t": "t",
    "th": "T", "v": "v", "w": "w", "y": "j", "z": "z", "zh": "Z",
    # letter-by-letter fallback (MockLLMProcessor's unknown-word path)
    "a": "a", "c": "k", "e": "E", "h": "h", "i": "I", "j": "dZ@",
    "o": "oU", "q": "k", "u": "V", "x": "ks",
}


def _resample(samples: List[int], factor: float) -> List[int]:
    """Linear-interpolation resample. factor > 1 raises pitch (shortens)."""
    if factor == 1.0 or not samples:
        return samples
    out_len = max(1, int(len(samples) / factor))
    out: List[int] = []
    for i in range(out_len):
        pos = i * factor
        lo = int(pos)
        hi = min(lo + 1, len(samples) - 1)
        frac = pos - lo
        out.append(int(samples[lo] * (1 - frac) + samples[hi] * frac))
    return out


def _strip_silence(samples: List[int], threshold: int = 300) -> List[int]:
    """Trim leading/trailing near-silence so duration fitting keeps the voiced part."""
    start = 0
    end = len(samples)
    while start < end and abs(samples[start]) < threshold:
        start += 1
    while end > start and abs(samples[end - 1]) < threshold:
        end -= 1
    return samples[start:end] if end > start else samples


def _fit_duration(samples: List[int], target_len: int) -> List[int]:
    """Trim or sustain (loop the middle with crossfade) to target_len samples."""
    fade = min(SAMPLE_RATE // 200, target_len)  # 5ms
    if not samples:
        return [0] * target_len
    if len(samples) >= target_len:
        out = samples[:target_len]
    else:
        # Loop the middle half to sustain the note
        loop = samples[len(samples) // 4: 3 * len(samples) // 4] or samples
        out = list(samples)
        while len(out) < target_len:
            for j, s in enumerate(loop):
                if len(out) >= target_len:
                    break
                if j < fade:  # crossfade the seam
                    s = int(s * j / fade + out[-1] * (1 - j / fade) * 0.5)
                out.append(s)
    # Fade out the tail to avoid clicks
    for i in range(max(0, len(out) - fade), len(out)):
        out[i] = int(out[i] * (len(out) - i) / fade)
    return out


class EspeakSynthesizer(AudioSynthesizer):
    """Real speech synthesis via the espeak-ng command-line tool.

    Each phoneme is rendered by espeak-ng in Kirshenbaum notation, then
    post-processed for singing: resampled to the exact target pitch,
    trimmed or looped to the event duration, with tremolo for vibrato,
    mixed noise for breathiness, and pitched copies for harmony.

    Requires the ``espeak-ng`` binary (``apt install espeak-ng`` /
    ``brew install espeak-ng``).
    """

    # Measured F0 of the default voice (en-us+f3) across espeak's 0-99
    # pitch parameter; interpolated to pick the parameter nearest a target
    # frequency. Other voices scale this curve by base_f0 / 203.4 (their
    # F0 at parameter 50).
    _PARAM_F0_TABLE = [
        (0, 137.9), (10, 148.1), (20, 158.4), (30, 171.7), (40, 186.0),
        (50, 203.4), (60, 222.8), (70, 245.4), (80, 270.9), (90, 300.6),
        (99, 330.3),
    ]
    _CACHE_MAX = 256

    def __init__(
        self,
        voice: str = "en-us+f3",
        speed: int = 130,
        base_f0: float = 203.4,
    ):
        if shutil.which("espeak-ng") is None:
            raise RuntimeError(
                "espeak-ng binary not found. Install it with "
                "'apt install espeak-ng' (Linux) or 'brew install espeak-ng' "
                "(macOS), or use tts_backend='mock'."
            )
        self.voice = voice
        self.speed = speed
        self.base_f0 = base_f0
        self._cache: Dict[Tuple[str, int], List[int]] = {}
        self._player: Optional[subprocess.Popen] = None

    def _param_to_f0(self, param: int) -> float:
        """Interpolate the voice's F0 for an espeak pitch parameter."""
        scale = self.base_f0 / 203.4
        table = self._PARAM_F0_TABLE
        if param <= table[0][0]:
            return table[0][1] * scale
        for (p0, f0), (p1, f1) in zip(table, table[1:]):
            if param <= p1:
                frac = (param - p0) / (p1 - p0)
                return (f0 + frac * (f1 - f0)) * scale
        return table[-1][1] * scale

    def _f0_to_param(self, hz: float) -> int:
        """Espeak pitch parameter whose F0 is nearest the target frequency."""
        scale = self.base_f0 / 203.4
        table = self._PARAM_F0_TABLE
        if hz <= table[0][1] * scale:
            return table[0][0]
        for (p0, f0), (p1, f1) in zip(table, table[1:]):
            if hz <= f1 * scale:
                frac = (hz - f0 * scale) / ((f1 - f0) * scale)
                return int(round(p0 + frac * (p1 - p0)))
        return table[-1][0]

    def _espeak_pcm(self, kirshenbaum: str, pitch_param: int) -> List[int]:
        """Run espeak-ng for one phoneme and return its PCM samples (cached)."""
        key = (kirshenbaum, pitch_param)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = subprocess.run(
            [
                "espeak-ng", "--stdout",
                "-v", self.voice,
                "-p", str(pitch_param),
                "-s", str(self.speed),
                f"[[{kirshenbaum}]]",
            ],
            capture_output=True,
        )
        # espeak streams the WAV, so the header's length field is bogus --
        # locate the data chunk and take everything after it.
        data_pos = result.stdout.find(b"data")
        samples: List[int] = []
        if result.returncode == 0 and data_pos != -1:
            pcm = result.stdout[data_pos + 8:]
            count = len(pcm) // 2
            samples = list(struct.unpack(f"<{count}h", pcm[: count * 2]))
            samples = _strip_silence(samples)
        if len(self._cache) >= self._CACHE_MAX:
            self._cache.clear()
        self._cache[key] = samples
        return samples

    def synthesize(self, event: PhonemeEvent) -> bytes:
        target_len = int(SAMPLE_RATE * event.duration_ms / 1000)
        if target_len == 0:
            return b""

        kirshenbaum = _ARPABET_TO_KIRSHENBAUM.get(event.phoneme.lower())
        if kirshenbaum is None:
            return struct.pack(f"<{target_len}h", *([0] * target_len))

        # Pick the espeak pitch parameter closest to the target pitch, then
        # resample for the exact frequency.
        param_int = self._f0_to_param(event.pitch_hz)
        actual_f0 = self._param_to_f0(param_int)
        factor = max(0.5, min(2.0, event.pitch_hz / actual_f0))

        samples = self._espeak_pcm(kirshenbaum, param_int)
        if not samples:
            return struct.pack(f"<{target_len}h", *([0] * target_len))

        samples = _resample(samples, factor)
        samples = _fit_duration(samples, target_len)

        # Harmony: mix pitched copies at the given semitone intervals
        if event.harmony_intervals:
            mixed = [float(s) for s in samples]
            for interval in event.harmony_intervals:
                voice = _fit_duration(
                    _resample(samples, 2 ** (interval / 12.0)), target_len
                )
                for i, s in enumerate(voice):
                    mixed[i] += 0.5 * s
            scale = 1.0 + 0.5 * len(event.harmony_intervals)
            samples = [int(s / scale) for s in mixed]

        # Vibrato: 5 Hz tremolo (amplitude modulation)
        if event.vibrato:
            for i in range(len(samples)):
                mod = 1.0 + 0.25 * math.sin(2 * math.pi * 5.0 * i / SAMPLE_RATE)
                samples[i] = int(samples[i] * mod)

        # Breathiness: blend in deterministic pseudo-noise (LCG)
        if event.breathiness > 0:
            state = 12345
            blend = min(1.0, event.breathiness) * 0.5
            for i in range(len(samples)):
                state = (state * 1103515245 + 12345) & 0x7FFFFFFF
                noise = (state / 0x3FFFFFFF - 1.0) * 8000
                samples[i] = int(samples[i] * (1 - blend) + noise * blend)

        # Volume scaling with clipping
        out: List[int] = []
        for s in samples:
            value = int(s * event.volume)
            out.append(max(-32768, min(32767, value)))
        return struct.pack(f"<{len(out)}h", *out)

    def play(self, audio_data: bytes) -> None:
        """Best-effort local playback by piping PCM to a persistent aplay.

        Silently does nothing when no audio player or device is available
        (e.g. in CI); the web server streams the PCM to the browser instead.
        """
        if not audio_data:
            return
        try:
            if self._player is None or self._player.poll() is not None:
                if shutil.which("aplay") is None:
                    return
                self._player = subprocess.Popen(
                    ["aplay", "-q", "-t", "raw", "-f", "S16_LE",
                     "-r", str(SAMPLE_RATE), "-c", "1"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if self._player.stdin is not None:
                self._player.stdin.write(audio_data)
                self._player.stdin.flush()
        except (OSError, BrokenPipeError, ValueError):
            self._player = None


class CoquiSynthesizer(AudioSynthesizer):
    """Stub for Coqui TTS integration."""

    def synthesize(self, event: PhonemeEvent) -> bytes:
        raise NotImplementedError("Coqui TTS integration pending")

    def play(self, audio_data: bytes) -> None:
        raise NotImplementedError("Coqui TTS integration pending")

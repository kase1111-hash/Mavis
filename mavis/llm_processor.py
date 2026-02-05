"""LLM Phoneme Processor -- converts Sheet Text tokens into timestamped phoneme events."""

import abc
from dataclasses import dataclass, field
from typing import List

from mavis.sheet_text import SheetTextToken


@dataclass
class PhonemeEvent:
    """A single phoneme with timing and prosody parameters."""

    phoneme: str  # IPA symbol
    start_ms: int = 0
    duration_ms: int = 100
    volume: float = 0.5  # 0.0 - 1.0
    pitch_hz: float = 220.0
    vibrato: bool = False
    breathiness: float = 0.0  # 0.0 - 1.0
    harmony_intervals: List[int] = field(default_factory=list)


class LLMProcessor(abc.ABC):
    """Abstract base class for LLM phoneme processors."""

    @abc.abstractmethod
    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        """Convert Sheet Text tokens into a list of PhonemeEvents."""


# Basic English-to-phoneme lookup (simplified ARPAbet-style, ~60 common words)
_WORD_PHONEMES = {
    "the": ["dh", "ax"],
    "a": ["ax"],
    "an": ["ae", "n"],
    "and": ["ae", "n", "d"],
    "is": ["ih", "z"],
    "are": ["aa", "r"],
    "was": ["w", "aa", "z"],
    "i": ["ay"],
    "you": ["y", "uw"],
    "it": ["ih", "t"],
    "in": ["ih", "n"],
    "to": ["t", "uw"],
    "of": ["ah", "v"],
    "for": ["f", "ao", "r"],
    "on": ["aa", "n"],
    "with": ["w", "ih", "th"],
    "this": ["dh", "ih", "s"],
    "that": ["dh", "ae", "t"],
    "not": ["n", "aa", "t"],
    "but": ["b", "ah", "t"],
    "my": ["m", "ay"],
    "all": ["ao", "l"],
    "so": ["s", "ow"],
    "up": ["ah", "p"],
    "sun": ["s", "ah", "n"],
    "rising": ["r", "ay", "z", "ih", "ng"],
    "rises": ["r", "ay", "z", "ih", "z"],
    "falling": ["f", "ao", "l", "ih", "ng"],
    "down": ["d", "aw", "n"],
    "hold": ["hh", "ow", "l", "d"],
    "note": ["n", "ow", "t"],
    "singing": ["s", "ih", "ng", "ih", "ng"],
    "together": ["t", "ax", "g", "eh", "dh", "er"],
    "again": ["ax", "g", "eh", "n"],
    "hello": ["hh", "ax", "l", "ow"],
    "world": ["w", "er", "l", "d"],
    "gently": ["jh", "eh", "n", "t", "l", "iy"],
    "said": ["s", "eh", "d"],
    "stop": ["s", "t", "aa", "p"],
    "twinkle": ["t", "w", "ih", "ng", "k", "ax", "l"],
    "little": ["l", "ih", "t", "ax", "l"],
    "star": ["s", "t", "aa", "r"],
    "how": ["hh", "aw"],
    "wonder": ["w", "ah", "n", "d", "er"],
    "what": ["w", "ah", "t"],
    "above": ["ax", "b", "ah", "v"],
    "like": ["l", "ay", "k"],
    "diamond": ["d", "ay", "ax", "m", "ax", "n", "d"],
    "sky": ["s", "k", "ay"],
}


def _word_to_phonemes(word: str) -> List[str]:
    """Look up phonemes for a word, falling back to letter-by-letter."""
    key = word.lower()
    if key in _WORD_PHONEMES:
        return list(_WORD_PHONEMES[key])
    # Fallback: one phoneme per letter (very rough)
    return [c.lower() for c in word if c.isalpha()]


# Emphasis -> prosody mappings
_EMPHASIS_VOLUME = {"none": 0.5, "soft": 0.3, "loud": 0.8, "shout": 1.0}
_EMPHASIS_BREATHINESS = {"none": 0.0, "soft": 0.6, "loud": 0.0, "shout": 0.0}
_EMPHASIS_PITCH_MULT = {"none": 1.0, "soft": 0.9, "loud": 1.1, "shout": 1.2}


class MockLLMProcessor(LLMProcessor):
    """Deterministic phoneme processor with no network calls.

    Uses a hardcoded English-to-phoneme dictionary and maps
    Sheet Text emphasis/sustain/harmony to prosody parameters.
    """

    def __init__(self, base_pitch_hz: float = 220.0, base_duration_ms: int = 100):
        self.base_pitch_hz = base_pitch_hz
        self.base_duration_ms = base_duration_ms

    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        events: List[PhonemeEvent] = []
        cursor_ms = 0

        for token in tokens:
            phonemes = _word_to_phonemes(token.text)
            volume = _EMPHASIS_VOLUME.get(token.emphasis, 0.5)
            breathiness = _EMPHASIS_BREATHINESS.get(token.emphasis, 0.0)
            pitch_mult = _EMPHASIS_PITCH_MULT.get(token.emphasis, 1.0)
            pitch_hz = self.base_pitch_hz * pitch_mult

            duration_ms = int(self.base_duration_ms * token.duration_modifier)
            vibrato = token.sustain
            harmony_intervals = [4, 7] if token.harmony else []

            for ph in phonemes:
                events.append(
                    PhonemeEvent(
                        phoneme=ph,
                        start_ms=cursor_ms,
                        duration_ms=duration_ms,
                        volume=volume,
                        pitch_hz=pitch_hz,
                        vibrato=vibrato,
                        breathiness=breathiness,
                        harmony_intervals=list(harmony_intervals),
                    )
                )
                cursor_ms += duration_ms

        return events


class LlamaLLMProcessor(LLMProcessor):
    """Stub for local Llama model integration via llama-cpp-python."""

    def __init__(self, model_path: str):
        self.model_path = model_path

    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        raise NotImplementedError("Llama integration pending")


class ClaudeLLMProcessor(LLMProcessor):
    """Stub for Anthropic Claude API integration."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        raise NotImplementedError("Claude integration pending")

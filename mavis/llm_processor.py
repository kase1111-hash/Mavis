"""LLM Phoneme Processor -- converts Sheet Text tokens into timestamped phoneme events."""

import abc
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from mavis.sheet_text import SheetTextToken

# The ARPAbet-style phoneme inventory Mavis can sing (see
# mavis.audio._ARPABET_TO_KIRSHENBAUM for the synthesis mapping).
VALID_PHONEMES = frozenset([
    # vowels
    "aa", "ae", "ah", "ao", "aw", "ax", "ay", "eh", "er", "ey",
    "ih", "iy", "ow", "oy", "uh", "uw",
    # consonants
    "b", "ch", "d", "dh", "f", "g", "hh", "jh", "k", "l", "m", "n",
    "ng", "p", "r", "s", "sh", "t", "th", "v", "w", "y", "z", "zh",
])


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


class WordPhonemeProcessor(LLMProcessor):
    """Base class for processors that convert one word at a time.

    Subclasses implement ``word_phonemes()``; the shared ``process()``
    applies the Sheet Text emphasis/sustain/harmony prosody mapping.
    """

    def __init__(self, base_pitch_hz: float = 220.0, base_duration_ms: int = 100):
        self.base_pitch_hz = base_pitch_hz
        self.base_duration_ms = base_duration_ms

    @abc.abstractmethod
    def word_phonemes(self, word: str) -> List[str]:
        """Return the phoneme sequence for a single word."""

    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        events: List[PhonemeEvent] = []
        cursor_ms = 0

        for token in tokens:
            phonemes = self.word_phonemes(token.text)
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


class MockLLMProcessor(WordPhonemeProcessor):
    """Deterministic phoneme processor with no network calls.

    Uses a hardcoded English-to-phoneme dictionary and maps
    Sheet Text emphasis/sustain/harmony to prosody parameters.
    """

    def word_phonemes(self, word: str) -> List[str]:
        return _word_to_phonemes(word)


# espeak-ng's Kirshenbaum-style output symbols (en-us voice) to the Mavis
# ARPAbet inventory. R-colored vowels carry the "r" inside the symbol, so
# some entries expand to two phonemes. Stress marks are stripped before
# lookup; unknown symbols are skipped.
_ESPEAK_TO_ARPABET: Dict[str, List[str]] = {
    "0": ["aa"], "3": ["er"], "3:": ["er"], ";": [], "|": [],
    "@": ["ax"], "@-": ["ax"], "@2": ["ax"], "@L": ["ax", "l"],
    "A:": ["aa"], "A@": ["aa", "r"], "D": ["dh"], "E": ["eh"],
    "I": ["ih"], "I#": ["ih"], "I2": ["ih"], "N": ["ng"],
    "O2": ["ao"], "O:": ["ao"], "O@": ["ao", "r"], "OI": ["oy"],
    "S": ["sh"], "T": ["th"], "U": ["uh"], "U@": ["uh", "r"],
    "V": ["ah"], "Z": ["zh"],
    "a": ["ae"], "a#": ["ax"], "aa": ["ae"],
    "aI": ["ay"], "aI3": ["ay", "er"], "aU": ["aw"],
    "e@": ["eh", "r"], "eI": ["ey"],
    "i": ["iy"], "i:": ["iy"], "i@": ["iy", "ax"],
    "o@": ["ow"], "oU": ["ow"],
    "t#": ["t"], "t2": ["t"], "tS": ["ch"], "dZ": ["jh"],
    "u:": ["uw"], "j": ["y"], "h": ["hh"],
    "b": ["b"], "d": ["d"], "f": ["f"], "g": ["g"], "k": ["k"],
    "l": ["l"], "m": ["m"], "n": ["n"], "p": ["p"], "r": ["r"],
    "s": ["s"], "t": ["t"], "v": ["v"], "w": ["w"], "z": ["z"],
}


class EspeakPhonemeProcessor(WordPhonemeProcessor):
    """Real grapheme-to-phoneme conversion via the espeak-ng CLI.

    Produces correct pronunciations for arbitrary English words (not just
    the mock's ~50-word dictionary) with no network access. Results are
    cached per word. Falls back to the mock dictionary if espeak fails.

    Requires the ``espeak-ng`` binary (``apt install espeak-ng`` /
    ``brew install espeak-ng``).
    """

    _CACHE_MAX = 4096

    def __init__(
        self,
        base_pitch_hz: float = 220.0,
        base_duration_ms: int = 100,
        voice: str = "en-us",
    ):
        super().__init__(base_pitch_hz, base_duration_ms)
        if shutil.which("espeak-ng") is None:
            raise RuntimeError(
                "espeak-ng binary not found. Install it with "
                "'apt install espeak-ng' (Linux) or 'brew install espeak-ng' "
                "(macOS), or use llm_backend='mock'."
            )
        self.voice = voice
        self._cache: Dict[str, List[str]] = {}

    def word_phonemes(self, word: str) -> List[str]:
        key = re.sub(r"[^a-zA-Z']", "", word).lower()
        if not key:
            return []
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)

        phonemes: List[str] = []
        try:
            result = subprocess.run(
                ["espeak-ng", "-x", "-q", "--sep=_", "-v", self.voice, key],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for symbol in result.stdout.replace(" ", "_").split("_"):
                    symbol = symbol.strip().replace("'", "").replace(",", "")
                    if symbol:
                        phonemes.extend(_ESPEAK_TO_ARPABET.get(symbol, []))
        except (OSError, subprocess.TimeoutExpired):
            phonemes = []

        if not phonemes:
            phonemes = _word_to_phonemes(key)

        if len(self._cache) >= self._CACHE_MAX:
            self._cache.clear()
        self._cache[key] = phonemes
        return list(phonemes)


# --- Shared LLM grapheme-to-phoneme prompt and parsing ---

_G2P_SYSTEM_PROMPT = (
    "You convert English words to phoneme sequences for a singing "
    "synthesizer. Use ONLY these lowercase ARPAbet-style symbols: "
    + ", ".join(sorted(VALID_PHONEMES))
    + ". Respond with JSON only: "
    '{"words": [{"word": "...", "phonemes": ["...", "..."]}]}'
)

_G2P_SCHEMA = {
    "type": "object",
    "properties": {
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "phonemes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["word", "phonemes"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["words"],
    "additionalProperties": False,
}


def _g2p_user_prompt(words: List[str]) -> str:
    return "Convert these words to phonemes: " + json.dumps(sorted(words))


def _parse_g2p_json(text: str) -> Dict[str, List[str]]:
    """Parse an LLM G2P response, validating phonemes against VALID_PHONEMES.

    Tolerates surrounding prose by extracting the outermost JSON object.
    Words with no valid phonemes are omitted (callers fall back).
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    result: Dict[str, List[str]] = {}
    for entry in data.get("words", []):
        if not isinstance(entry, dict):
            continue
        word = str(entry.get("word", "")).lower()
        raw = entry.get("phonemes", [])
        if not word or not isinstance(raw, list):
            continue
        phonemes = [str(p).lower() for p in raw if str(p).lower() in VALID_PHONEMES]
        if phonemes:
            result[word] = phonemes
    return result


def _default_word_fallback() -> Callable[[str], List[str]]:
    """Best available local G2P: espeak-ng if installed, else the dictionary."""
    if shutil.which("espeak-ng") is not None:
        return EspeakPhonemeProcessor().word_phonemes
    return _word_to_phonemes


class ClaudeLLMProcessor(WordPhonemeProcessor):
    """Grapheme-to-phoneme conversion via the Anthropic Claude API.

    Each ``process()`` call batches every not-yet-cached word in the token
    list into a single API request with a structured-output JSON schema, so
    repeated words never re-query. On any API failure (or a word the model
    couldn't convert) it falls back to local G2P (espeak-ng if installed,
    else the mock dictionary), so gameplay never breaks.

    Requires ``pip install anthropic`` and an API key (``ANTHROPIC_API_KEY``
    or the ``api_key`` argument), unless a ``client`` is injected.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-opus-4-8",
        base_pitch_hz: float = 220.0,
        base_duration_ms: int = 100,
        client: Optional[Any] = None,
        fallback: Optional[Callable[[str], List[str]]] = None,
    ):
        super().__init__(base_pitch_hz, base_duration_ms)
        self.api_key = api_key
        self.model = model
        self._cache: Dict[str, List[str]] = {}
        self._fallback = fallback or _default_word_fallback()
        if client is not None:
            self._client = client
        else:
            try:
                import anthropic
            except ImportError:
                raise RuntimeError(
                    "The 'anthropic' package is required for llm_backend="
                    "'claude'. Install it with 'pip install anthropic' "
                    "(or 'pip install mavis[llm-cloud]')."
                )
            self._client = anthropic.Anthropic(api_key=api_key) if api_key \
                else anthropic.Anthropic()

    def prewarm(self, words: List[str]) -> None:
        """Fetch phonemes for a word list in one API call (e.g. song lyrics)."""
        self._fetch_words([w for w in words if self._normalize(w)])

    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        self._fetch_words([t.text for t in tokens])
        return super().process(tokens)

    def word_phonemes(self, word: str) -> List[str]:
        key = self._normalize(word)
        if not key:
            return []
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)
        # Not resolved by the batch fetch (API failure or unknown word):
        # fall back locally and cache so we don't retry every occurrence.
        phonemes = self._fallback(key)
        self._cache[key] = phonemes
        return list(phonemes)

    @staticmethod
    def _normalize(word: str) -> str:
        return re.sub(r"[^a-zA-Z']", "", word).lower()

    def _fetch_words(self, words: List[str]) -> None:
        """Batch-fetch phonemes for all uncached words in one API call."""
        pending = sorted({
            key for key in (self._normalize(w) for w in words)
            if key and key not in self._cache
        })
        if not pending:
            return
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=_G2P_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _g2p_user_prompt(pending)}],
                output_config={"format": {"type": "json_schema", "schema": _G2P_SCHEMA}},
            )
        except Exception:
            # Rate limits, network failures, auth errors: leave the words
            # uncached-by-API; word_phonemes() falls back locally.
            return
        if getattr(response, "stop_reason", None) == "refusal":
            return
        text = next(
            (b.text for b in response.content if getattr(b, "type", "") == "text"),
            "",
        )
        self._cache.update(_parse_g2p_json(text))


class LlamaLLMProcessor(WordPhonemeProcessor):
    """Grapheme-to-phoneme conversion via a local llama-cpp-python model.

    Same batching, caching, validation, and local-fallback behavior as
    ClaudeLLMProcessor, but runs a local GGUF model instead of a network
    API. Requires ``pip install llama-cpp-python`` and a model file,
    unless a ``completion_fn`` (prompt -> generated text) is injected.
    """

    def __init__(
        self,
        model_path: str,
        base_pitch_hz: float = 220.0,
        base_duration_ms: int = 100,
        completion_fn: Optional[Callable[[str], str]] = None,
        fallback: Optional[Callable[[str], List[str]]] = None,
    ):
        super().__init__(base_pitch_hz, base_duration_ms)
        self.model_path = model_path
        self._cache: Dict[str, List[str]] = {}
        self._fallback = fallback or _default_word_fallback()
        if completion_fn is not None:
            self._complete = completion_fn
        else:
            try:
                from llama_cpp import Llama
            except ImportError:
                raise RuntimeError(
                    "The 'llama-cpp-python' package is required for "
                    "llm_backend='llama'. Install it with "
                    "'pip install llama-cpp-python' "
                    "(or 'pip install mavis[llm-local]')."
                )
            llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)

            def _complete(prompt: str) -> str:
                out = llm(prompt, max_tokens=1024, temperature=0.0)
                return str(out["choices"][0]["text"])

            self._complete = _complete

    def process(self, tokens: List[SheetTextToken]) -> List[PhonemeEvent]:
        self._fetch_words([t.text for t in tokens])
        return super().process(tokens)

    def word_phonemes(self, word: str) -> List[str]:
        key = ClaudeLLMProcessor._normalize(word)
        if not key:
            return []
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)
        phonemes = self._fallback(key)
        self._cache[key] = phonemes
        return list(phonemes)

    def _fetch_words(self, words: List[str]) -> None:
        pending = sorted({
            key for key in (ClaudeLLMProcessor._normalize(w) for w in words)
            if key and key not in self._cache
        })
        if not pending:
            return
        prompt = _G2P_SYSTEM_PROMPT + "\n\n" + _g2p_user_prompt(pending) + "\nJSON:"
        try:
            text = self._complete(prompt)
        except Exception:
            return
        self._cache.update(_parse_g2p_json(text))

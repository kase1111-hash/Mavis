"""Tests for mavis.llm_processor."""

import shutil

import pytest

from mavis.llm_processor import (
    _ESPEAK_TO_ARPABET,
    _parse_g2p_json,
    VALID_PHONEMES,
    ClaudeLLMProcessor,
    EspeakPhonemeProcessor,
    LlamaLLMProcessor,
    MockLLMProcessor,
    PhonemeEvent,
)
from mavis.sheet_text import SheetTextToken


def _token(text, emphasis="none", sustain=False, harmony=False, dur=1.0):
    return SheetTextToken(text=text, emphasis=emphasis, sustain=sustain,
                          harmony=harmony, duration_modifier=dur)


def test_mock_basic_conversion():
    proc = MockLLMProcessor()
    tokens = [_token("hello")]
    events = proc.process(tokens)
    assert len(events) > 0
    assert all(isinstance(e, PhonemeEvent) for e in events)


def test_loud_volume():
    proc = MockLLMProcessor()
    events = proc.process([_token("sun", emphasis="loud")])
    for e in events:
        assert e.volume > 0.7


def test_soft_breathiness():
    proc = MockLLMProcessor()
    events = proc.process([_token("gently", emphasis="soft")])
    for e in events:
        assert e.breathiness > 0.5
        assert e.volume < 0.4


def test_sustain_vibrato():
    proc = MockLLMProcessor()
    events = proc.process([_token("hold", sustain=True, dur=2.0)])
    for e in events:
        assert e.vibrato is True
        assert e.duration_ms == 200  # base 100 * 2.0


def test_harmony_intervals():
    proc = MockLLMProcessor()
    events = proc.process([_token("together", harmony=True)])
    for e in events:
        assert len(e.harmony_intervals) > 0
        assert 4 in e.harmony_intervals
        assert 7 in e.harmony_intervals


def test_sequential_non_overlapping():
    proc = MockLLMProcessor()
    events = proc.process([_token("hello"), _token("world")])
    for i in range(1, len(events)):
        assert events[i].start_ms >= events[i - 1].start_ms + events[i - 1].duration_ms


def test_shout_max_volume():
    proc = MockLLMProcessor()
    events = proc.process([_token("stop", emphasis="shout")])
    for e in events:
        assert e.volume == 1.0


def test_empty_tokens():
    proc = MockLLMProcessor()
    events = proc.process([])
    assert events == []


# --- Espeak grapheme-to-phoneme backend ---

_HAS_ESPEAK = shutil.which("espeak-ng") is not None
requires_espeak = pytest.mark.skipif(not _HAS_ESPEAK, reason="espeak-ng not installed")


def test_espeak_map_targets_are_valid_phonemes():
    """Every espeak symbol must map onto the singable phoneme inventory."""
    for symbol, phonemes in _ESPEAK_TO_ARPABET.items():
        for ph in phonemes:
            assert ph in VALID_PHONEMES, f"{symbol!r} maps to unknown {ph!r}"


def test_valid_phonemes_are_singable():
    """Every phoneme in the inventory must have a synthesis mapping."""
    from mavis.audio import _ARPABET_TO_KIRSHENBAUM
    missing = VALID_PHONEMES - set(_ARPABET_TO_KIRSHENBAUM)
    assert not missing, f"unsingable phonemes: {sorted(missing)}"


@requires_espeak
def test_espeak_g2p_known_words():
    proc = EspeakPhonemeProcessor()
    for word in ["twinkle", "wonder", "diamond", "say"]:
        phonemes = proc.word_phonemes(word)
        assert phonemes, word
        assert all(p in VALID_PHONEMES for p in phonemes), (word, phonemes)


@requires_espeak
def test_espeak_g2p_beats_letter_fallback():
    """espeak must produce a real pronunciation for words outside the
    mock dictionary (e.g. silent letters), not one phoneme per letter."""
    proc = EspeakPhonemeProcessor()
    phonemes = proc.word_phonemes("knight")  # /naIt/ - 3 phonemes, not 6
    assert phonemes[0] == "n"
    assert len(phonemes) <= 4


@requires_espeak
def test_espeak_g2p_caches():
    proc = EspeakPhonemeProcessor()
    first = proc.word_phonemes("serenade")
    assert "serenade" in proc._cache
    assert proc.word_phonemes("serenade") == first


@requires_espeak
def test_espeak_g2p_full_song_vocabulary():
    """Every word in the 10-song library must convert to valid phonemes."""
    import glob
    import json as jsonlib
    proc = EspeakPhonemeProcessor()
    for path in glob.glob("songs/*.json"):
        for tok in jsonlib.load(open(path))["tokens"]:
            phonemes = proc.word_phonemes(tok["text"])
            bad = [p for p in phonemes if p not in VALID_PHONEMES]
            assert not bad, (path, tok["text"], bad)


@requires_espeak
def test_espeak_processor_applies_prosody():
    proc = EspeakPhonemeProcessor()
    events = proc.process([_token("SUN", emphasis="loud")])
    assert events
    assert all(e.volume == 0.8 for e in events)


def test_espeak_missing_binary_raises(monkeypatch):
    monkeypatch.setattr("mavis.llm_processor.shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="espeak-ng"):
        EspeakPhonemeProcessor()


# --- Shared G2P response parsing ---

def test_parse_g2p_json_valid():
    text = '{"words": [{"word": "Sun", "phonemes": ["S", "ah", "n"]}]}'
    assert _parse_g2p_json(text) == {"sun": ["s", "ah", "n"]}


def test_parse_g2p_json_filters_invalid_phonemes():
    text = '{"words": [{"word": "x", "phonemes": ["zz9", "k"]}, {"word": "y", "phonemes": ["nope"]}]}'
    assert _parse_g2p_json(text) == {"x": ["k"]}


def test_parse_g2p_json_tolerates_prose_and_garbage():
    assert _parse_g2p_json("no json here") == {}
    assert _parse_g2p_json("Sure! {\"words\": [{\"word\": \"a\", \"phonemes\": [\"ax\"]}]} Done.") == {"a": ["ax"]}
    assert _parse_g2p_json("{broken") == {}


# --- Claude API backend (fake client; no network) ---

class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeResponse:
    stop_reason = "end_turn"

    def __init__(self, text):
        self.content = [_FakeBlock(text)]


class _FakeMessages:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class _FakeClient:
    def __init__(self, responses):
        self.messages = _FakeMessages(responses)


def _claude(responses, **kwargs):
    kwargs.setdefault("fallback", lambda w: ["ax"])
    return ClaudeLLMProcessor(client=_FakeClient(responses), **kwargs)


def test_claude_converts_words():
    proc = _claude([_FakeResponse(
        '{"words": [{"word": "sun", "phonemes": ["s", "ah", "n"]}]}'
    )])
    events = proc.process([_token("SUN", emphasis="loud")])
    assert [e.phoneme for e in events] == ["s", "ah", "n"]
    assert all(e.volume == 0.8 for e in events)


def test_claude_batches_and_caches():
    proc = _claude([_FakeResponse(
        '{"words": [{"word": "sun", "phonemes": ["s", "ah", "n"]},'
        ' {"word": "moon", "phonemes": ["m", "uw", "n"]}]}'
    )])
    proc.process([_token("sun"), _token("moon")])
    proc.process([_token("moon"), _token("sun")])  # all cached now
    assert len(proc._client.messages.calls) == 1
    call = proc._client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert "output_config" in call


def test_claude_falls_back_on_api_error():
    proc = _claude([RuntimeError("network down")])
    events = proc.process([_token("sun")])
    assert events
    assert all(e.phoneme == "ax" for e in events)  # injected fallback
    # Failure is cached; a new API call is still attempted for NEW words only
    proc.process([_token("sun")])
    assert len(proc._client.messages.calls) == 1


def test_claude_falls_back_on_refusal():
    resp = _FakeResponse("")
    resp.stop_reason = "refusal"
    proc = _claude([resp])
    events = proc.process([_token("sun")])
    assert all(e.phoneme == "ax" for e in events)


def test_claude_prewarm():
    proc = _claude([_FakeResponse(
        '{"words": [{"word": "twinkle", "phonemes": ["t", "w", "ih", "ng", "k", "ax", "l"]}]}'
    )])
    proc.prewarm(["twinkle", "twinkle"])
    assert len(proc._client.messages.calls) == 1
    assert proc.word_phonemes("twinkle")[0] == "t"


# --- Llama local backend (fake completion; no model file) ---

def test_llama_converts_words():
    def fake_complete(prompt):
        assert "sun" in prompt
        return 'JSON: {"words": [{"word": "sun", "phonemes": ["s", "ah", "n"]}]}'

    proc = LlamaLLMProcessor(
        "/fake/model.gguf", completion_fn=fake_complete, fallback=lambda w: ["ax"]
    )
    events = proc.process([_token("sun")])
    assert [e.phoneme for e in events] == ["s", "ah", "n"]


def test_llama_falls_back_on_garbage_output():
    proc = LlamaLLMProcessor(
        "/fake/model.gguf",
        completion_fn=lambda p: "I cannot help with that",
        fallback=lambda w: ["ax"],
    )
    events = proc.process([_token("sun")])
    assert all(e.phoneme == "ax" for e in events)


# --- Pipeline integration ---

@requires_espeak
def test_pipeline_espeak_llm_backend():
    from mavis.config import MavisConfig
    from mavis.pipeline import create_pipeline

    pipe = create_pipeline(MavisConfig(llm_backend="espeak"))
    pipe.feed_text("psychology rhythm knight ")  # none in mock dictionary
    for _ in range(5):
        pipe.tick(elapsed_ms=0)
    pipe.tick(elapsed_ms=2000)
    assert pipe.take_audio()

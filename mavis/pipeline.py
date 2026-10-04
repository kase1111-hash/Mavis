"""Pipeline orchestrator -- wires all components into a single runnable pipeline."""

import time
from typing import Dict, List, Optional

from mavis.audio import AudioSynthesizer, EspeakSynthesizer, MockAudioSynthesizer
from mavis.config import MavisConfig
from mavis.difficulty import DifficultySettings, get_difficulty
from mavis.export import PerformanceRecording
from mavis.input_buffer import InputBuffer
from mavis.llm_processor import (
    ClaudeLLMProcessor,
    EspeakPhonemeProcessor,
    LlamaLLMProcessor,
    LLMProcessor,
    MockLLMProcessor,
    PhonemeEvent,
)
from mavis.output_buffer import OutputBuffer
from mavis.sheet_text import SheetTextToken, parse
from mavis.voice import VoiceProfile, get_voice

# A partial word is sent to the parser anyway once the typist has paused this
# long, so the last word of a line is sung without a trailing space.
WORD_IDLE_FLUSH_MS = 1000


class MavisPipeline:
    """End-to-end pipeline: InputBuffer -> Parser -> LLM -> OutputBuffer -> Audio.

    Call ``feed()`` to push keystrokes in, and ``tick()`` to advance the
    pipeline by one processing frame.

    When ``recording`` is not None, all events (keystrokes, tokens, phonemes,
    buffer states) are logged for later export to the Prosody-Protocol format.
    """

    def __init__(self, config: MavisConfig):
        self.config = config

        # Apply difficulty settings if specified
        self.difficulty: Optional[DifficultySettings] = None
        input_cap = config.input_buffer_capacity
        output_cap = config.output_buffer_capacity
        if config.difficulty_name is not None:
            self.difficulty = get_difficulty(config.difficulty_name)
            input_cap = self.difficulty.input_buffer_capacity
            output_cap = self.difficulty.output_buffer_capacity

        # Apply voice profile if specified
        self.voice: Optional[VoiceProfile] = None
        if config.voice_name is not None:
            self.voice = get_voice(config.voice_name)

        self.input_buffer = InputBuffer(capacity=input_cap)

        # Build output buffer with difficulty-specific thresholds
        if self.difficulty is not None:
            self.output_buffer = OutputBuffer(
                capacity=output_cap,
                low_threshold=self.difficulty.optimal_zone_low,
                high_threshold=self.difficulty.optimal_zone_high,
            )
        else:
            self.output_buffer = OutputBuffer(capacity=output_cap)
        self.llm: LLMProcessor = _create_llm(config)
        self.audio: AudioSynthesizer = _create_audio(config.tts_backend)

        self._last_tokens: List[SheetTextToken] = []
        self._last_phoneme: Optional[PhonemeEvent] = None
        self._last_audio: Optional[bytes] = None

        # How many input chars to consume per tick
        self._chunk_size = 8

        # Consumed chars waiting for their word to be complete. Parsing
        # whatever happened to be consumed would split words mid-typing and
        # sing them letter by letter.
        self._pending_chars: List[Dict] = []
        self._pending_idle_ms: int = 0

        # Drain is time-based: phonemes are "sung" at a fixed rate per second
        # of real time regardless of tick frequency, so buffer management
        # stays winnable at human typing speed at any frame rate.
        multiplier = 1.0
        if self.difficulty is not None:
            multiplier = self.difficulty.drain_rate_multiplier
        self.drain_rate: float = config.base_drain_rate * multiplier
        self._drain_accum: float = 0.0
        self._popped_last_tick: int = 0
        self._pending_audio: List[bytes] = []

        # Optional performance recording (for Prosody-Protocol export)
        self.recording: Optional[PerformanceRecording] = None
        self._start_time: Optional[float] = None

    def start_recording(self, song_id: Optional[str] = None) -> PerformanceRecording:
        """Begin recording a performance for Prosody-Protocol export.

        Returns the PerformanceRecording instance being populated.
        """
        diff_name = self.config.hardware.difficulty
        if self.difficulty is not None:
            diff_name = self.difficulty.name.lower()
        self.recording = PerformanceRecording(
            song_id=song_id,
            hardware_profile=self.config.hardware.name,
            difficulty=diff_name,
        )
        self._start_time = time.monotonic()
        return self.recording

    def stop_recording(self) -> Optional[PerformanceRecording]:
        """Stop recording and return the completed PerformanceRecording."""
        rec = self.recording
        self.recording = None
        self._start_time = None
        return rec

    def _elapsed_ms(self) -> int:
        """Milliseconds since recording started (or 0 if not recording)."""
        if self._start_time is None:
            return 0
        return int((time.monotonic() - self._start_time) * 1000)

    def feed(self, char: str, modifiers: Optional[Dict[str, bool]] = None) -> None:
        """Push a single character into the input buffer."""
        self.input_buffer.push(char, modifiers)
        if self.recording is not None:
            self.recording.record_keystroke(
                self._elapsed_ms(), char, modifiers or {}
            )

    def feed_text(self, text: str) -> None:
        """Convenience: push an entire string, inferring shift from case."""
        for c in text:
            mods = {"shift": c.isupper(), "ctrl": False, "alt": False}
            self.feed(c, mods)

    def tick(self, elapsed_ms: int = 33) -> Dict:
        """Advance the pipeline by ``elapsed_ms`` of real time.

        1. Consume a chunk from the input buffer.
        2. Parse the words completed so far into Sheet Text tokens.
        3. Process tokens through the LLM for phoneme events.
        4. Push phoneme events into the output buffer.
        5. Drain events at ``drain_rate`` phonemes/sec and synthesize audio.

        Returns the current pipeline state dict.
        """
        # Step 1: Consume input, keeping only complete words
        chars = self._complete_words(
            self.input_buffer.consume(self._chunk_size), elapsed_ms
        )

        # Steps 2-4: Parse, LLM, voice, push to output buffer
        self._process(chars)

        # Step 5: Drain and synthesize at drain_rate phonemes per second.
        # Cap elapsed time so a stalled caller (e.g. a throttled browser tab)
        # cannot dump a burst of drains in one tick.
        self._drain_accum += self.drain_rate * min(elapsed_ms, 1000) / 1000.0
        to_pop = int(self._drain_accum)
        self._drain_accum -= to_pop

        self._popped_last_tick = 0
        for _ in range(to_pop):
            event = self.output_buffer.pop()
            if event is None:
                break
            self._popped_last_tick += 1
            self._last_phoneme = event
            self._last_audio = self.audio.synthesize(event)
            self.audio.play(self._last_audio)
            self._pending_audio.append(self._last_audio)
            if self.recording is not None:
                self.recording.record_phoneme(self._elapsed_ms(), event)

        # Record buffer state
        if self.recording is not None:
            self.recording.record_buffer_state(
                self._elapsed_ms(), self.output_buffer.state()
            )

        return self.state()

    def flush(self) -> None:
        """Process everything typed so far, including an unfinished last word.

        Call at the end of a performance so a final word typed without a
        trailing space is still sung.
        """
        chars = self._pending_chars + self.input_buffer.consume(self.input_buffer.size())
        self._pending_chars = []
        self._pending_idle_ms = 0
        self._process(chars)

    def _complete_words(self, chars: List[Dict], elapsed_ms: int) -> List[Dict]:
        """Queue newly consumed chars and return those ready to be parsed.

        Text is ready up to the end of the last complete word, except that a
        trailing run of loud words is held back until the run ends, since a
        run of 2+ loud words is sung as a shout. Everything is released once
        the typist pauses for ``WORD_IDLE_FLUSH_MS``.
        """
        pending = self._pending_chars
        pending.extend(chars)
        self._pending_idle_ms = 0 if chars else self._pending_idle_ms + elapsed_ms

        if (
            self._pending_idle_ms >= WORD_IDLE_FLUSH_MS
            or len(pending) >= self.input_buffer.capacity
        ):
            cut = len(pending)
        else:
            cut = 0
            word_start = 0
            for i, ch in enumerate(pending):
                if not ch["char"].isspace():
                    continue
                word = pending[word_start:i]
                word_start = i + 1
                if not word:
                    continue
                word_tokens = parse(word)
                if not word_tokens or word_tokens[-1].emphasis != "loud":
                    cut = i + 1

        self._pending_chars = pending[cut:]
        return pending[:cut]

    def _process(self, chars: List[Dict]) -> None:
        """Parse chars into tokens, convert to phonemes, and queue them."""
        tokens = parse(chars) if chars else []
        if not tokens:
            return
        self._last_tokens = tokens
        if self.recording is not None:
            now = self._elapsed_ms()
            for tok in tokens:
                self.recording.record_token(now, tok)

        events = self.llm.process(tokens)
        if self.voice is not None:
            events = [_apply_voice(ev, self.voice) for ev in events]
        if events:
            self.output_buffer.push(events)

    def state(self) -> Dict:
        """Return combined pipeline state."""
        buf_state = self.output_buffer.state()
        return {
            "input_buffer_level": self.input_buffer.level(),
            "input_buffer_size": self.input_buffer.size(),
            "output_buffer_level": buf_state.level,
            "output_buffer_status": buf_state.status,
            "output_buffer_size": self.output_buffer.size(),
            "output_drain_rate": buf_state.drain_rate,
            "output_fill_rate": buf_state.fill_rate,
            "last_tokens": [t.text for t in self._last_tokens],
            "last_phoneme": self._last_phoneme.phoneme if self._last_phoneme else None,
            "phonemes_popped": self._popped_last_tick,
        }

    def take_audio(self) -> bytes:
        """Return PCM audio synthesized since the last call and clear it.

        Concatenated 16-bit mono PCM at mavis.audio.SAMPLE_RATE, suitable
        for streaming to a client for playback.
        """
        if not self._pending_audio:
            return b""
        audio = b"".join(self._pending_audio)
        self._pending_audio.clear()
        return audio


def _create_llm(config: MavisConfig) -> LLMProcessor:
    backend = config.llm_backend
    if backend == "mock":
        return MockLLMProcessor()
    if backend == "espeak":
        return EspeakPhonemeProcessor()
    if backend == "claude":
        return ClaudeLLMProcessor(model=config.claude_model)
    if backend == "llama":
        if not config.llama_model_path:
            raise ValueError("llm_backend='llama' requires config.llama_model_path")
        return LlamaLLMProcessor(config.llama_model_path)
    raise ValueError(f"Unknown LLM backend: {backend!r}")


def _create_audio(backend: str) -> AudioSynthesizer:
    if backend == "mock":
        return MockAudioSynthesizer()
    if backend == "espeak":
        return EspeakSynthesizer()
    raise ValueError(f"Unknown TTS backend: {backend!r}")


def _apply_voice(event: PhonemeEvent, voice: VoiceProfile) -> PhonemeEvent:
    """Apply voice profile adjustments to a PhonemeEvent."""
    return PhonemeEvent(
        phoneme=event.phoneme,
        start_ms=event.start_ms,
        duration_ms=event.duration_ms,
        volume=min(1.0, event.volume * voice.volume_scale),
        pitch_hz=event.pitch_hz * (voice.base_pitch_hz / 220.0),
        vibrato=event.vibrato,
        breathiness=max(event.breathiness, voice.breathiness),
        harmony_intervals=list(event.harmony_intervals),
    )


def create_pipeline(config: Optional[MavisConfig] = None) -> MavisPipeline:
    """Factory function to create a pipeline with default or custom config."""
    if config is None:
        config = MavisConfig()
    return MavisPipeline(config)

"""Pipeline orchestrator -- wires all components into a single runnable pipeline."""

import time
from typing import Dict, List, Optional

from mavis.audio import AudioSynthesizer, MockAudioSynthesizer
from mavis.config import MavisConfig
from mavis.export import PerformanceRecording
from mavis.input_buffer import InputBuffer
from mavis.llm_processor import (
    LLMProcessor,
    MockLLMProcessor,
    PhonemeEvent,
)
from mavis.output_buffer import OutputBuffer
from mavis.sheet_text import SheetTextToken, parse


class MavisPipeline:
    """End-to-end pipeline: InputBuffer -> Parser -> LLM -> OutputBuffer -> Audio.

    Call ``feed()`` to push keystrokes in, and ``tick()`` to advance the
    pipeline by one processing frame.

    When ``recording`` is not None, all events (keystrokes, tokens, phonemes,
    buffer states) are logged for later export to the Prosody-Protocol format.
    """

    def __init__(self, config: MavisConfig):
        self.config = config
        self.input_buffer = InputBuffer(capacity=config.input_buffer_capacity)
        self.output_buffer = OutputBuffer(capacity=config.output_buffer_capacity)
        self.llm: LLMProcessor = _create_llm(config.llm_backend)
        self.audio: AudioSynthesizer = _create_audio(config.tts_backend)

        self._last_tokens: List[SheetTextToken] = []
        self._last_phoneme: Optional[PhonemeEvent] = None
        self._last_audio: Optional[bytes] = None

        # How many input chars to consume per tick
        self._chunk_size = 8

        # Optional performance recording (for Prosody-Protocol export)
        self.recording: Optional[PerformanceRecording] = None
        self._start_time: Optional[float] = None

    def start_recording(self, song_id: Optional[str] = None) -> PerformanceRecording:
        """Begin recording a performance for Prosody-Protocol export.

        Returns the PerformanceRecording instance being populated.
        """
        self.recording = PerformanceRecording(
            song_id=song_id,
            hardware_profile=self.config.hardware.name,
            difficulty=self.config.hardware.difficulty,
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
        """Advance the pipeline by one frame.

        1. Consume a chunk from the input buffer.
        2. Parse into Sheet Text tokens.
        3. Process tokens through the LLM for phoneme events.
        4. Push phoneme events into the output buffer.
        5. Pop one event and synthesize audio.

        Returns the current pipeline state dict.
        """
        # Step 1: Consume input
        chars = self.input_buffer.consume(self._chunk_size)

        # Step 2: Parse
        tokens = parse(chars) if chars else []
        if tokens:
            self._last_tokens = tokens
            if self.recording is not None:
                now = self._elapsed_ms()
                for tok in tokens:
                    self.recording.record_token(now, tok)

        # Step 3: LLM processing
        events: List[PhonemeEvent] = []
        if tokens:
            events = self.llm.process(tokens)

        # Step 4: Push to output buffer
        if events:
            self.output_buffer.push(events)

        # Step 5: Pop and synthesize
        self._last_phoneme = self.output_buffer.pop()
        if self._last_phoneme is not None:
            self._last_audio = self.audio.synthesize(self._last_phoneme)
            self.audio.play(self._last_audio)
            if self.recording is not None:
                self.recording.record_phoneme(self._elapsed_ms(), self._last_phoneme)
        else:
            self._last_audio = None

        # Record buffer state
        if self.recording is not None:
            self.recording.record_buffer_state(
                self._elapsed_ms(), self.output_buffer.state()
            )

        return self.state()

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
        }


def _create_llm(backend: str) -> LLMProcessor:
    if backend == "mock":
        return MockLLMProcessor()
    raise ValueError(f"Unknown LLM backend: {backend!r}")


def _create_audio(backend: str) -> AudioSynthesizer:
    if backend == "mock":
        return MockAudioSynthesizer()
    raise ValueError(f"Unknown TTS backend: {backend!r}")


def create_pipeline(config: Optional[MavisConfig] = None) -> MavisPipeline:
    """Factory function to create a pipeline with default or custom config."""
    if config is None:
        config = MavisConfig()
    return MavisPipeline(config)

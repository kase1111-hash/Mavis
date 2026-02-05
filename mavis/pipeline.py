"""Pipeline orchestrator -- wires all components into a single runnable pipeline."""

from typing import Dict, List, Optional

from mavis.audio import AudioSynthesizer, MockAudioSynthesizer
from mavis.config import MavisConfig
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

    def feed(self, char: str, modifiers: Optional[Dict[str, bool]] = None) -> None:
        """Push a single character into the input buffer."""
        self.input_buffer.push(char, modifiers)

    def feed_text(self, text: str) -> None:
        """Convenience: push an entire string, inferring shift from case."""
        for c in text:
            mods = {"shift": c.isupper(), "ctrl": False, "alt": False}
            self.input_buffer.push(c, mods)

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
        else:
            self._last_audio = None

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

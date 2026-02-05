# CLAUDE.md - Agent Guide for Mavis

## Project Summary

Mavis is a vocal typing instrument that converts keyboard input with prosody markup ("Sheet Text") into singing via an LLM + TTS pipeline. It is a Python 3.8+ project. Phase 1 (Playable Alpha) is implemented with mock backends, a full pipeline, scoring, and two working demos.

## Repository Structure

```
/
├── mavis/                        # Core Python package
│   ├── __init__.py               # Package root, version = "0.1.0"
│   ├── input_buffer.py           # Keystroke FIFO queue
│   ├── sheet_text.py             # Sheet Text parser (markup -> tokens)
│   ├── config.py                 # Hardware profiles and MavisConfig
│   ├── llm_processor.py          # LLM phoneme processor (mock + stubs)
│   ├── output_buffer.py          # Phoneme output buffer (game mechanic)
│   ├── audio.py                  # Audio synthesis (mock + stubs)
│   ├── pipeline.py               # Pipeline orchestrator (wires all components)
│   ├── scoring.py                # Score tracker and grading
│   └── songs.py                  # Song loader (JSON -> Song dataclass)
├── tests/                        # pytest test suite (73 tests)
│   ├── test_input_buffer.py
│   ├── test_sheet_text.py
│   ├── test_config.py
│   ├── test_llm_processor.py
│   ├── test_output_buffer.py
│   ├── test_audio.py
│   ├── test_pipeline.py
│   ├── test_scoring.py
│   └── test_songs.py
├── demos/
│   ├── vocal_typing_demo.py      # Non-interactive pipeline visualization
│   └── interactive_vocal_typing.py  # Curses-based interactive typing demo
├── songs/
│   └── twinkle.json              # First playable song
├── pyproject.toml                # Python packaging config
├── .gitignore
├── README.md
├── spec.md
├── EXECUTION_GUIDE.md
├── LICENSE
└── CLAUDE.md                     # This file
```

## Key Concepts

- **Sheet Text**: Prosody markup notation embedded in typed text. CAPS = loud, `_underscores_` = soft, `...` = vibrato, `[brackets]` = harmony, ALL CAPS = shout.
- **Pipeline**: Input Buffer -> Sheet Text Parser -> LLM Phoneme Processor -> Output Buffer -> Audio Synthesis.
- **Buffer management**: The core gameplay mechanic. Users control vocal output by managing typing speed and pause timing to keep the buffer in an optimal zone.
- **Latency as gameplay**: The 600ms-1.5s processing delay is intentional -- users read ahead in the Sheet Text, absorbing latency through lookahead.

## Tech Stack

- **Language**: Python 3.8+
- **Packaging**: pyproject.toml with optional dependency groups
- **LLM**: MockLLMProcessor (working), llama-cpp-python and Claude API (stubs)
- **TTS**: MockAudioSynthesizer (sine waves, working), espeak-ng and Coqui (stubs)
- **Interface**: curses (working terminal demo)
- **Testing**: pytest (73 tests passing)

## Development Commands

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run the non-interactive pipeline demo
python3 demos/vocal_typing_demo.py

# Run the interactive typing demo
python3 demos/interactive_vocal_typing.py

# Run with a song loaded
python3 demos/interactive_vocal_typing.py songs/twinkle.json

# Import check
python3 -c "import mavis; print(mavis.__version__)"
```

## Development Guidelines

- Use `pyproject.toml` for all packaging config. Optional dependency groups: `dev`, `llm-local`, `llm-cloud`, `tts-coqui`, `web`.
- Every module in `mavis/` must have a corresponding test file in `tests/`.
- Follow the data models in `spec.md` Section 7 and the dataclasses in `mavis/llm_processor.py` and `mavis/output_buffer.py`.
- Demo scripts live in `demos/`. Songs live in `songs/` as JSON files.
- The README references `IMPLEMENTATION.md` and `CONTRIBUTING.md` which do not exist yet.

## Adding a New Sheet Text Markup

1. Add the markup definition to the Sheet Text table in both `README.md` and `spec.md`.
2. Update the parser in `mavis/sheet_text.py` to recognize the new token pattern.
3. Update `mavis/llm_processor.py` to map the new prosody cue to phoneme parameters.
4. Add corresponding synthesis behavior in `mavis/audio.py`.
5. Add tests for parsing and processing the new markup.

## Adding a New Song

1. Create a JSON file in `songs/` following the format of `twinkle.json`.
2. Required fields: `title`, `bpm`, `difficulty`, `sheet_text`, `tokens`.
3. Each token needs: `text`, `emphasis`, `sustain`, `harmony`, `duration_modifier`.
4. Test with: `python3 -c "from mavis.songs import load_song; print(load_song('songs/yourfile.json'))"`.

## Architecture Notes

- `InputBuffer` uses `collections.deque(maxlen=capacity)` for O(1) push/consume with automatic overflow.
- Sheet Text parser uses a two-pass approach: first pass groups chars into words and detects markup, second pass promotes consecutive "loud" tokens to "shout".
- `MockLLMProcessor` uses a hardcoded English-to-phoneme dictionary (~50 words) with emphasis-to-prosody mapping.
- `OutputBuffer` tracks fill/drain rates over a 2-second sliding window for real-time status display.
- `MavisPipeline.tick()` runs the full cycle: consume input -> parse -> LLM -> buffer -> synthesize.

## Related Ecosystem

- **prosody-protocol**: Markup language and training dataset.
- **intent-engine**: Prosody-aware AI processing.
- **Agent-OS**: Constitutional AI governance layer.

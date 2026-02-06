# CLAUDE.md - Agent Guide for Mavis

## Project Summary

Mavis is a vocal typing instrument that converts keyboard input with prosody markup ("Sheet Text") into singing via an LLM + TTS pipeline. It is a Python 3.8+ project. Phase 1 (Playable Alpha) is implemented with mock backends, a full pipeline, scoring, and two working demos. Performance data exports to the [Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol) IML format.

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
│   ├── songs.py                  # Song loader (JSON -> Song dataclass)
│   └── export.py                 # Prosody-Protocol IML/dataset export
├── tests/                        # pytest test suite (95 tests)
│   ├── test_input_buffer.py
│   ├── test_sheet_text.py
│   ├── test_config.py
│   ├── test_llm_processor.py
│   ├── test_output_buffer.py
│   ├── test_audio.py
│   ├── test_pipeline.py
│   ├── test_scoring.py
│   ├── test_songs.py
│   └── test_export.py
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

## Prosody-Protocol Integration

Mavis is a **data source** for the [Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol) ecosystem. Every performance session can be recorded and exported as:

- **IML (Intent Markup Language)** XML documents -- the protocol's core format for preserving prosodic intent alongside text. Sheet Text markup maps directly to IML tags: `<prosody>` for emphasis/volume, `<emphasis>` for stress levels, `<pause>` for sustain.
- **Dataset entries** conforming to the protocol's `dataset-entry.schema.json` -- JSON records with source=`"mavis"`, IML markup, emotion labels, and metadata.
- **Training feature vectors** (7-dimensional) compatible with the protocol's `MavisBridge.extract_training_features()`.

### Key mapping: Sheet Text -> IML

| Sheet Text | IML Output |
|------------|-----------|
| CAPS (loud) | `<prosody volume="+6dB" pitch="+10%">` |
| `_soft_` | `<prosody volume="-6dB" quality="breathy">` |
| ALL CAPS (shout) | `<prosody volume="+12dB" pitch="+20%" quality="tense">` |
| `...` (sustain) | `<pause duration="..."/>` |
| `[harmony]` | (recorded in metadata, no direct IML tag) |

### Export module: `mavis/export.py`

- `PerformanceRecording` -- records keystrokes, tokens, phonemes, and buffer states with timestamps.
- `tokens_to_iml()` -- converts Sheet Text tokens to IML XML.
- `phoneme_events_to_iml()` -- converts PhonemeEvents to IML with per-word prosody deviation.
- `recording_to_dataset_entry()` -- produces a dataset entry dict matching the protocol schema.
- `export_dataset()` -- writes a full dataset directory (`metadata.json` + `entries/*.json`).
- `extract_training_features()` -- 7-dim feature vector: [mean_pitch, pitch_range, mean_volume, volume_range, mean_breathiness, speech_rate, vibrato_ratio].
- `infer_emotion()` -- heuristic emotion classification (neutral/angry/joyful/sad/calm) matching the protocol's MavisBridge logic.

### Pipeline recording

`MavisPipeline` supports opt-in performance recording:
```python
pipe = create_pipeline(config)
rec = pipe.start_recording(song_id="twinkle")
# ... feed characters, tick ...
rec = pipe.stop_recording()
rec.consent = True  # required before export
export_performance(rec, "output/session.json")
```

### Prosody-Protocol SDK (optional)

Install with `pip install prosody-protocol` or `pip install mavis[prosody]`. When the SDK is installed, its `MavisBridge`, `IMLValidator`, and `DatasetLoader` can be used for stricter validation. The export module works without the SDK by generating compatible output directly.

## Key Concepts

- **Sheet Text**: Prosody markup notation embedded in typed text. CAPS = loud, `_underscores_` = soft, `...` = vibrato, `[brackets]` = harmony, ALL CAPS = shout.
- **Pipeline**: Input Buffer -> Sheet Text Parser -> LLM Phoneme Processor -> Output Buffer -> Audio Synthesis.
- **Buffer management**: The core gameplay mechanic. Users control vocal output by managing typing speed and pause timing to keep the buffer in an optimal zone.
- **Latency as gameplay**: The 600ms-1.5s processing delay is intentional -- users read ahead in the Sheet Text, absorbing latency through lookahead.
- **IML (Intent Markup Language)**: The XML interchange format defined by Prosody-Protocol for preserving prosodic annotations. Mavis exports to this format.

## Tech Stack

- **Language**: Python 3.8+
- **Packaging**: pyproject.toml with optional dependency groups
- **LLM**: MockLLMProcessor (working), llama-cpp-python and Claude API (stubs)
- **TTS**: MockAudioSynthesizer (sine waves, working), espeak-ng and Coqui (stubs)
- **Interface**: curses (working terminal demo)
- **Data format**: Prosody-Protocol IML 1.0 (XML) + dataset-entry JSON schema
- **Testing**: pytest (95 tests passing)

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

# Export a test IML document
python3 -c "from mavis.export import tokens_to_iml; from mavis.sheet_text import SheetTextToken; print(tokens_to_iml([SheetTextToken(text='SUN', emphasis='loud')]))"
```

## Development Guidelines

- Use `pyproject.toml` for all packaging config. Optional dependency groups: `dev`, `llm-local`, `llm-cloud`, `tts-coqui`, `web`, `prosody`.
- Every module in `mavis/` must have a corresponding test file in `tests/`.
- Follow the data models in `spec.md` Section 7 and the dataclasses in `mavis/llm_processor.py` and `mavis/output_buffer.py`.
- Demo scripts live in `demos/`. Songs live in `songs/` as JSON files.
- All export output must conform to the Prosody-Protocol schemas at https://github.com/kase1111-hash/Prosody-Protocol/tree/main/schemas.
- The README references `IMPLEMENTATION.md` and `CONTRIBUTING.md` which do not exist yet.

## Adding a New Sheet Text Markup

1. Add the markup definition to the Sheet Text table in both `README.md` and `spec.md`.
2. Update the parser in `mavis/sheet_text.py` to recognize the new token pattern.
3. Update `mavis/llm_processor.py` to map the new prosody cue to phoneme parameters.
4. Add corresponding synthesis behavior in `mavis/audio.py`.
5. Add the IML mapping in `mavis/export.py` (`_EMPHASIS_TO_IML` and `_EMPHASIS_TO_LEVEL` dicts).
6. Add tests for parsing, processing, and IML export of the new markup.

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
- `MavisPipeline.tick()` runs the full cycle: consume input -> parse -> LLM -> buffer -> synthesize. When recording is active, every event is timestamped and stored in the `PerformanceRecording`.
- `mavis/export.py` maps Mavis data to Prosody-Protocol IML without requiring the `prosody_protocol` SDK at runtime, but produces output the SDK can validate.

## Related Ecosystem

- **[Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol)**: IML specification, JSON schemas, Python SDK, and training infrastructure. Mavis is the primary data source -- every performance generates IML-annotated training data that feeds back into this protocol.
- **intent-engine**: Prosody-aware AI processing (consumes IML documents from Prosody-Protocol).
- **Agent-OS**: Constitutional AI governance layer (uses intent-engine for prosody-aware verification).

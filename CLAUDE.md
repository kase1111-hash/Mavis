# CLAUDE.md - Agent Guide for Mavis

## Project Summary

Mavis is a vocal typing instrument that converts keyboard input with prosody markup ("Sheet Text") into singing via an LLM + TTS pipeline. It is a Python 3.8+ project. Phase 1 (Playable Alpha) and Phase 2 (Game Polish) are implemented with mock backends, a full pipeline, scoring, 10-song library, difficulty levels, leaderboards, voice customization, tutorial mode, and two working demos. Performance data exports to the [Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol) IML format.

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
│   ├── export.py                 # Prosody-Protocol IML/dataset export
│   ├── song_browser.py           # Song list/filter/display (Phase 2)
│   ├── difficulty.py             # Difficulty presets and settings (Phase 2)
│   ├── leaderboard.py            # Local JSON leaderboard storage (Phase 2)
│   ├── voice.py                  # Voice profile presets and persistence (Phase 2)
│   └── tutorial.py               # 7-lesson tutorial with progress tracking (Phase 2)
├── tests/                        # pytest test suite (152 tests)
│   ├── test_input_buffer.py
│   ├── test_sheet_text.py
│   ├── test_config.py
│   ├── test_llm_processor.py
│   ├── test_output_buffer.py
│   ├── test_audio.py
│   ├── test_pipeline.py
│   ├── test_scoring.py
│   ├── test_songs.py
│   ├── test_export.py
│   ├── test_song_browser.py
│   ├── test_difficulty.py
│   ├── test_leaderboard.py
│   ├── test_voice.py
│   └── test_tutorial.py
├── demos/
│   ├── vocal_typing_demo.py      # Non-interactive pipeline visualization
│   └── interactive_vocal_typing.py  # Curses-based interactive demo with menus
├── songs/                        # 10-song library across 3 difficulty tiers
│   ├── twinkle.json              # Easy: Twinkle Twinkle Little Star
│   ├── mary_lamb.json            # Easy: Mary Had a Little Lamb
│   ├── row_boat.json             # Easy: Row Row Row Your Boat
│   ├── amazing_grace.json        # Medium: Amazing Grace
│   ├── hallelujah.json           # Medium: Hallelujah
│   ├── bohemian.json             # Medium: Bohemian Rhapsody (Excerpt)
│   ├── somewhere_rainbow.json    # Medium: Somewhere Over the Rainbow
│   ├── dont_stop.json            # Hard: Don't Stop Believin' (Excerpt)
│   ├── nessun_dorma.json         # Hard: Nessun Dorma (Excerpt)
│   └── rap_god.json              # Hard: Rap God (Excerpt)
├── pyproject.toml                # Python packaging config
├── .gitignore
├── README.md
├── spec.md
├── EXECUTION_GUIDE.md
├── LICENSE
└── CLAUDE.md                     # This file
```

## Phase 2 Modules

### Difficulty System (`mavis/difficulty.py`)
- `DifficultySettings` dataclass with buffer capacities, zone thresholds, point values, drain rate multipliers.
- 4 presets: Easy (wide zone, gentle penalties), Medium (standard), Hard (narrow zone, harsh penalties), Expert (razor-thin zone).
- Pipeline auto-applies difficulty: adjusts input/output buffer capacities and optimal zone thresholds.
- `get_difficulty(name)` and `list_difficulties()` for lookup.

### Song Browser (`mavis/song_browser.py`)
- `browse_songs(directory, difficulty)` -- list and filter songs from the `songs/` directory.
- `group_by_difficulty(songs)` -- organize songs into easy/medium/hard groups.
- `song_summary(song)` and `format_song_list(songs)` -- terminal display formatting.

### Leaderboard (`mavis/leaderboard.py`)
- `Leaderboard` class backed by a JSON file at `~/.mavis/leaderboards.json`.
- `submit(entry)` returns rank (1-based), auto-sorts and enforces max entries per song.
- `get_scores(song_id, difficulty, limit)` for filtered retrieval.
- `format_scores(song_id)` for terminal display.

### Voice Customization (`mavis/voice.py`)
- `VoiceProfile` dataclass: base_pitch_hz, pitch_range, vibrato_depth/rate, breathiness, volume_scale, timbre.
- 6 presets: Default, Alto, Soprano, Bass, Whisper, Robot.
- Pipeline applies voice profile to PhonemeEvents (pitch scaling, breathiness, volume).
- `save_voice_preference()` / `load_voice_preference()` persists to `~/.mavis/voice.json`.

### Tutorial Mode (`mavis/tutorial.py`)
- 7 progressive lessons: Basic Typing, Emphasis, Soft Voice, Sustain, Harmony, Buffer Management, Full Performance.
- Each lesson has steps with instructions, practice text, and hints.
- `TutorialProgress` tracks completion and best grade per lesson (no downgrade).
- `format_lesson_list(progress)` for terminal display with grade markers.

### Interactive Demo Enhancements
- Main menu: Play a Song, Tutorial, Leaderboard, Settings, Quit.
- Song browser with difficulty-sorted list and curses navigation.
- Settings menu for difficulty and voice selection.
- Leaderboard display screen.
- Tutorial menu with lesson selection.
- Results screen with automatic leaderboard submission.

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
- **Difficulty levels**: 4 presets (Easy/Medium/Hard/Expert) that adjust buffer sizes, zone thresholds, and scoring penalties.
- **Voice profiles**: 6 presets that modify synthesis pitch, vibrato, breathiness, and volume.

## Tech Stack

- **Language**: Python 3.8+
- **Packaging**: pyproject.toml with optional dependency groups
- **LLM**: MockLLMProcessor (working), llama-cpp-python and Claude API (stubs)
- **TTS**: MockAudioSynthesizer (sine waves, working), espeak-ng and Coqui (stubs)
- **Interface**: curses (working terminal demo with menus)
- **Data format**: Prosody-Protocol IML 1.0 (XML) + dataset-entry JSON schema
- **Testing**: pytest (152 tests passing)

## Development Commands

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run the non-interactive pipeline demo
python3 demos/vocal_typing_demo.py

# Run the interactive typing demo (main menu)
python3 demos/interactive_vocal_typing.py

# Run with a song loaded directly
python3 demos/interactive_vocal_typing.py songs/twinkle.json

# Import check
python3 -c "import mavis; print(mavis.__version__)"

# Export a test IML document
python3 -c "from mavis.export import tokens_to_iml; from mavis.sheet_text import SheetTextToken; print(tokens_to_iml([SheetTextToken(text='SUN', emphasis='loud')]))"

# List all songs
python3 -c "from mavis.song_browser import browse_songs, format_song_list; print(format_song_list(browse_songs('songs')))"

# List difficulty presets
python3 -c "from mavis.difficulty import list_difficulties; [print(f'{d.name}: {d.description}') for d in list_difficulties()]"
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
4. Difficulty must be `"easy"`, `"medium"`, or `"hard"`.
5. Test with: `python3 -c "from mavis.songs import load_song; print(load_song('songs/yourfile.json'))"`.

## Architecture Notes

- `InputBuffer` uses `collections.deque(maxlen=capacity)` for O(1) push/consume with automatic overflow.
- Sheet Text parser uses a two-pass approach: first pass groups chars into words and detects markup, second pass promotes consecutive "loud" tokens to "shout".
- `MockLLMProcessor` uses a hardcoded English-to-phoneme dictionary (~50 words) with emphasis-to-prosody mapping.
- `OutputBuffer` tracks fill/drain rates over a 2-second sliding window for real-time status display. Supports custom low/high thresholds for difficulty integration.
- `MavisPipeline.tick()` runs the full cycle: consume input -> parse -> LLM -> apply voice profile -> buffer -> synthesize. When recording is active, every event is timestamped and stored in the `PerformanceRecording`.
- `MavisPipeline.__init__()` reads `config.difficulty_name` and `config.voice_name` to auto-apply difficulty settings (buffer capacities, zone thresholds) and voice profile (pitch scaling, breathiness).
- `mavis/export.py` maps Mavis data to Prosody-Protocol IML without requiring the `prosody_protocol` SDK at runtime, but produces output the SDK can validate.
- `Leaderboard` persists to `~/.mavis/leaderboards.json` and auto-sorts/trims entries per song.
- Voice profiles modify PhonemeEvents through `_apply_voice()` which scales pitch proportionally to base_pitch_hz and blends breathiness.

## Related Ecosystem

- **[Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol)**: IML specification, JSON schemas, Python SDK, and training infrastructure. Mavis is the primary data source -- every performance generates IML-annotated training data that feeds back into this protocol.
- **intent-engine**: Prosody-aware AI processing (consumes IML documents from Prosody-Protocol).
- **Agent-OS**: Constitutional AI governance layer (uses intent-engine for prosody-aware verification).

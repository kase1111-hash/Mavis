# CLAUDE.md - Agent Guide for Mavis

## Project Summary

Mavis is a vocal typing instrument that converts keyboard input with prosody markup ("Sheet Text") into singing via an LLM + TTS pipeline. It is a Python 3.8+ project. Phases 1 (Playable Alpha), 2 (Game Polish), 3 (Platform Launch), and 4 (Ecosystem Integration) are implemented with mock backends, a full pipeline, scoring, 10-song library, difficulty levels, leaderboards, voice customization, tutorial mode, web interface (FastAPI + WebSocket), mobile client (React Native), cloud save, multiplayer, user-generated content, intent-engine integration, researcher API, and institutional licensing. Performance data exports to the [Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol) IML format.

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
│   ├── tutorial.py               # 7-lesson tutorial with progress tracking (Phase 2)
│   ├── cloud.py                  # User accounts, auth, cloud sync (Phase 3)
│   ├── multiplayer.py            # Rooms, players, duet splitting (Phase 3)
│   ├── song_editor.py            # Song creation, validation, community library (Phase 3)
│   ├── intent_bridge.py          # Intent-engine prosody analysis bridge (Phase 4)
│   ├── researcher_api.py         # Anonymized performance data API (Phase 4)
│   └── licensing.py              # License tiers, key validation, feature gating (Phase 4)
├── web/                          # FastAPI web interface (Phase 3)
│   ├── __init__.py
│   ├── server.py                 # REST API + WebSocket gameplay + auth + UGC endpoints
│   └── static/
│       ├── index.html            # Single-page app (7 screens)
│       ├── app.js                # WebSocket client with keyboard capture
│       └── style.css             # Dark theme UI
├── mobile/                       # React Native mobile client (Phase 3)
│   ├── package.json
│   ├── App.js                    # Main component with screens
│   └── src/
│       ├── WebSocketClient.js    # WebSocket connection wrapper
│       ├── BufferDisplay.js      # Buffer bar components
│       ├── SheetTextView.js      # Song text display
│       └── AudioPlayer.js        # Audio playback stub
├── tests/                        # pytest test suite (281 tests)
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
│   ├── test_tutorial.py
│   ├── test_cloud.py
│   ├── test_multiplayer.py
│   ├── test_song_editor.py
│   ├── test_export_phase4.py
│   ├── test_intent_bridge.py
│   ├── test_researcher_api.py
│   └── test_licensing.py
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

## Phase 3 Modules

### Web Version (`web/server.py` + `web/static/`)
- **FastAPI backend** with REST API and WebSocket gameplay.
- `GameSession` wraps `MavisPipeline` + `ScoreTracker` for per-client state.
- WebSocket `/ws/play`: real-time gameplay (start/key/tick/stop protocol).
- WebSocket `/ws/room/{room_id}`: multiplayer room with opponent state broadcasts.
- REST endpoints: `GET /api/songs`, `GET /api/leaderboard/{song_id}`, `POST /api/leaderboard/{song_id}`.
- Auth endpoints: `POST /auth/register`, `POST /auth/login`, `GET /api/profile`, `PUT /api/progress`.
- UGC endpoints: `POST /api/songs/upload`, `GET /api/songs/community`, `POST /api/songs/{id}/rate`, `POST /api/songs/{id}/flag`.
- **Static frontend**: single-page app with 7 screens (menu, song browser, game, results, leaderboard, settings, multiplayer). Dark theme, monospace design.
- Run with: `uvicorn web.server:app --reload` (requires `pip install mavis[web]`).

### Mobile Client (`mobile/`)
- **React Native** thin client connecting to the same FastAPI backend.
- `App.js`: screens for menu, settings, song browser, game, results.
- `WebSocketClient.js`: connection lifecycle and JSON serialization.
- `BufferDisplay.js`: color-coded input/output buffer bars.
- `SheetTextView.js`: monospace Sheet Text display.
- `AudioPlayer.js`: stub for future client-side audio.
- Touch gesture mapping: tap=keypress, long press=sustain, swipe up=CAPS, swipe down=soft, two-finger=harmony.

### Cloud Save (`mavis/cloud.py`)
- `UserProfile` dataclass with preferences, tutorial progress, personal bests.
- `UserStore`: JSON-file-backed user storage at `~/.mavis/users.json`.
- `register()` / `authenticate()` with salted SHA-256 password hashing.
- `generate_token()` / `verify_token()` for session authentication (HMAC-style with expiry).
- `SyncPayload` + `sync()` for offline-first data merge: last-write-wins for preferences, max-score-wins for bests, no grade downgrade for tutorial.
- Production path: swap to bcrypt + JWT + SQLAlchemy (optional deps in `cloud` group).

### Multiplayer (`mavis/multiplayer.py`)
- `Room`: holds up to 2 players with separate pipelines and score trackers.
- `Player`: wraps pipeline + tracker, provides `feed_char()`, `tick_idle()`, `result()`.
- `RoomManager`: create, look up, remove, and clean up rooms.
- `DuetSplitter`: splits songs for duet mode.
  - `split(song)`: harmony lines to player 2, alternating phrases otherwise.
  - `split_tokens(tokens)`: harmony tokens to player 2, non-harmony alternated.
- Modes: `competitive` (same song, highest score wins) and `duet` (split parts).
- `get_winner()` returns winner name or None for ties.

### User-Generated Content (`mavis/song_editor.py`)
- `SongDraft`: create and validate songs (title, bpm 40-300, difficulty, sheet text max 5000 chars).
- `validate()` returns error list; `to_song()` parses Sheet Text into tokens; `to_json()` / `save()` for export.
- `CommunityLibrary`: JSON-backed storage at `~/.mavis/community.json`.
- `submit(draft)` adds songs; `browse(sort_by, difficulty, limit, offset)` for paginated browsing.
- `rate(entry_id, 1-5)` for star ratings; `flag(entry_id)` for moderation (auto-hides at 3 flags).
- Sort options: `rating`, `newest`, `title`.

## Phase 4 Modules

### Enhanced Export (`mavis/export.py` additions)
- `export_dataset_jsonl()`: bulk export to JSONL for ML training pipelines, consent-gated.
- `generate_audio_for_recording()`: generate WAV audio files from performance phoneme events.
- `validate_iml()`: validate IML XML strings with structural checks; delegates to SDK `IMLValidator` when installed.
- `_write_wav()`: write raw PCM data as 16-bit mono WAV files.

### Intent-Engine Bridge (`mavis/intent_bridge.py`)
- `IntentBridge`: connects to the intent-engine REST API for prosody-aware analysis.
- Falls back to local heuristic analysis when the service is unavailable.
- `analyze()` / `analyze_recording()`: returns dominant_emotion, energy_curve, intent_confidence, coaching_suggestions.
- `get_feedback()`: generates human-readable feedback text from analysis results.
- `get_coaching()`: extracts coaching suggestions (dynamic contrast, sustain usage, energy building).
- Local analysis detects "triumphant" pattern (rising energy ending loud) beyond the 5 basic emotions.
- `_compute_energy_curve()`: segments volume over time into N segments for visualization.

### Researcher API (`mavis/researcher_api.py`)
- `AnonymizedPerformance`: stripped of player names and raw keystrokes; retains tokens, phonemes, IML, features.
- `PerformanceStore`: JSON-backed storage at `~/.mavis/performances.json`.
  - `record()` / `get()` / `query()` with filtering by song_id, difficulty, min_score, pagination.
  - `statistics()`: aggregate stats (total, averages by song, difficulty/emotion distributions).
  - `prosody_map()`: average feature vectors grouped by emotion label.
- `APIKeyStore`: manages researcher API keys with SHA-256 hashing.
  - `register()` returns plaintext key; `validate()` checks hash.
  - `check_rate_limit()`: sliding window (1 minute), 100 requests/minute default.
  - `revoke()` / `list_keys()` for key management.
- Web endpoints: `POST /api/v1/register`, `GET /api/v1/performances`, `GET /api/v1/performances/{id}`, `GET /api/v1/statistics`, `GET /api/v1/prosody-map`.

### Institutional Licensing (`mavis/licensing.py`)
- 3 tiers: Free (personal, local only), Institutional (cloud, multiplayer, researcher API), Research (bulk export, admin dashboard).
- `generate_license_key()` / `validate_license_key()`: HMAC-SHA256 signed keys with tier, institution, expiry.
- `LicenseInfo`: tracks tier, expiry, activation, offline grace period (7 days).
  - `is_active()` / `has_feature()` / `to_dict()` for feature gating.
- `LicenseManager`: JSON persistence at `~/.mavis/license.json`.
  - `activate()` / `deactivate()` / `check_online()` / `list_features()` / `usage_report()`.
- Web endpoints: `GET /api/license/tiers`, `GET /api/license/current`, `POST /api/license/activate`, `POST /api/license/deactivate`.

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
- **Web**: FastAPI + WebSocket (real-time gameplay), static HTML/JS frontend
- **Mobile**: React Native thin client
- **Interface**: curses (working terminal demo with menus)
- **Data format**: Prosody-Protocol IML 1.0 (XML) + dataset-entry JSON schema
- **Testing**: pytest (281 tests passing)

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

# Run the web server (requires fastapi, uvicorn)
pip install fastapi uvicorn websockets
uvicorn web.server:app --reload --port 8000
# Then open http://localhost:8000 in a browser
```

## Development Guidelines

- Use `pyproject.toml` for all packaging config. Optional dependency groups: `dev`, `llm-local`, `llm-cloud`, `tts-coqui`, `web`, `cloud`, `prosody`.
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

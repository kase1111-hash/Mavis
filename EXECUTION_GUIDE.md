# Mavis Execution Guide

Step-by-step implementation plan for every phase of the project, from empty repo to full ecosystem integration.

---

## Phase 0: Project Scaffolding

Set up the repository structure, packaging, and developer tooling before writing any application code.

### 0.1 Python Package Setup

Create the core package directory and packaging configuration.

```
mavis/
├── __init__.py          # Package root, version string
├── input_buffer.py      # Step 1.1
├── sheet_text.py        # Step 1.2
├── llm_processor.py     # Step 1.4
├── output_buffer.py     # Step 1.5
├── audio.py             # Step 1.6
├── pipeline.py          # Step 1.7 (wires everything together)
└── config.py            # Hardware profiles, defaults
```

**Files to create:**

1. `pyproject.toml` -- Minimum fields:
   - `[project]` name = `"mavis"`, requires-python = `">=3.8"`
   - Dependencies: none yet (add as each component lands)
   - `[project.optional-dependencies]` for `dev` extras (pytest, ruff, mypy)
   - `[project.scripts]` entry point: `mavis = "mavis.cli:main"` (add later when CLI exists)

2. `mavis/__init__.py` -- Package init with `__version__ = "0.1.0"`.

3. `.gitignore` -- Python defaults: `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `*.egg-info/`, `.mypy_cache/`.

4. `requirements-dev.txt` -- `pytest`, `ruff`, `mypy` for early development before `pyproject.toml` extras are wired.

### 0.2 Test Infrastructure

```
tests/
├── __init__.py
├── test_sheet_text.py
├── test_input_buffer.py
├── test_output_buffer.py
├── test_llm_processor.py
└── test_pipeline.py
```

- Configure pytest in `pyproject.toml` under `[tool.pytest.ini_options]`.
- Every module built in Phase 1 must have a corresponding test file before the step is considered complete.

### 0.3 Demo Directory

```
demos/
├── vocal_typing_demo.py
└── interactive_vocal_typing.py
```

Create placeholder files that print "Not yet implemented" so the README's Quick Start section doesn't point at missing files.

### 0.4 Verification

```bash
python -m pytest tests/ --tb=short   # Should pass (no tests yet, 0 collected)
python -c "import mavis; print(mavis.__version__)"  # Should print 0.1.0
```

---

## Phase 1: Playable Alpha

Build every pipeline component end-to-end, wire them together, then ship one playable demo.

### Step 1.1 -- Input Buffer

**File:** `mavis/input_buffer.py`

Purpose: Capture keystrokes, store typed text, and provide a FIFO queue that feeds into the Sheet Text parser.

**What to build:**

- Class `InputBuffer`
  - `push(char: str, modifiers: dict)` -- Append a character with modifier state (shift, ctrl, alt).
  - `peek(n: int) -> list[dict]` -- Look at next N characters without consuming.
  - `consume(n: int) -> list[dict]` -- Remove and return next N characters.
  - `level() -> float` -- Return buffer fill ratio (0.0 to 1.0).
  - `capacity: int` -- Maximum characters the buffer holds (configurable, default 256).
  - Internal storage: `collections.deque` with `maxlen`.

- Each buffered item is a dict: `{"char": str, "shift": bool, "ctrl": bool, "alt": bool, "timestamp_ms": int}`.

**Tests (`tests/test_input_buffer.py`):**

- Push characters, verify consume returns them in order.
- Verify level() is 0.0 when empty, 1.0 when full.
- Verify overflow behavior (oldest items dropped when over capacity).
- Verify modifier flags are stored correctly.

### Step 1.2 -- Sheet Text Parser

**File:** `mavis/sheet_text.py`

Purpose: Convert raw buffered characters into structured Sheet Text tokens (see spec.md Section 7.1).

**What to build:**

- Dataclass `SheetTextToken`:
  ```python
  @dataclass
  class SheetTextToken:
      text: str
      emphasis: str       # "none" | "soft" | "loud" | "shout"
      sustain: bool
      harmony: bool
      duration_modifier: float
  ```

- Function `parse(chars: list[dict]) -> list[SheetTextToken]`:
  - Detect CAPS (shift held) -> emphasis = "loud".
  - Detect ALL CAPS run (multiple consecutive uppercase without lowercase) -> emphasis = "shout".
  - Detect `_..._` wrapping -> emphasis = "soft".
  - Detect `...` sequence -> sustain = True, duration_modifier = 2.0.
  - Detect `[...]` wrapping or ctrl held -> harmony = True.
  - Everything else -> emphasis = "none", sustain = False, harmony = False, duration_modifier = 1.0.

**Tests (`tests/test_sheet_text.py`):**

- Parse `"the SUN rises"` -> tokens with "none", "loud", "none" emphasis.
- Parse `"I SAID STOP"` -> all tokens have "shout" emphasis.
- Parse `"falling _gently_"` -> "gently" has "soft" emphasis.
- Parse `"hold... this"` -> "hold" token has sustain = True.
- Parse `"singing [together]"` -> "together" has harmony = True.
- Mixed markup: `"the SUN... is falling _down_"` produces correct token sequence.

### Step 1.3 -- Config and Hardware Profiles

**File:** `mavis/config.py`

Purpose: Central configuration for hardware profiles, buffer sizes, and latency targets.

**What to build:**

- Dataclass `HardwareProfile`:
  ```python
  @dataclass
  class HardwareProfile:
      name: str
      total_latency_ms: int
      buffer_window_s: float
      difficulty: str        # "easy" | "medium" | "hard"
  ```

- Predefined profiles (from spec.md Section 4.3):
  - `LAPTOP_CPU = HardwareProfile("Laptop (CPU)", 800, 5.0, "easy")`
  - `DESKTOP_GPU = HardwareProfile("Desktop (GPU)", 200, 2.0, "medium")`
  - `SERVER_GPU = HardwareProfile("Server (GPU)", 80, 1.0, "hard")`
  - `CLOUD_API = HardwareProfile("Cloud API", 150, 2.5, "medium")`

- Dataclass `MavisConfig`:
  - `hardware: HardwareProfile`
  - `input_buffer_capacity: int` (default 256)
  - `output_buffer_capacity: int` (default 128)
  - `llm_backend: str` ("mock" | "llama" | "claude")
  - `tts_backend: str` ("mock" | "espeak" | "coqui" | "elevenlabs")

### Step 1.4 -- LLM Phoneme Processor

**File:** `mavis/llm_processor.py`

Purpose: Take Sheet Text tokens and produce timestamped phoneme events (see spec.md Section 7.2).

**What to build:**

- Dataclass `PhonemeEvent`:
  ```python
  @dataclass
  class PhonemeEvent:
      phoneme: str          # IPA symbol
      start_ms: int
      duration_ms: int
      volume: float         # 0.0 - 1.0
      pitch_hz: float
      vibrato: bool
      breathiness: float    # 0.0 - 1.0
      harmony_intervals: list[int]  # semitone offsets
  ```

- Abstract base class `LLMProcessor`:
  - `process(tokens: list[SheetTextToken]) -> list[PhonemeEvent]`

- Concrete class `MockLLMProcessor(LLMProcessor)`:
  - Deterministic, no network calls. For every token, generate a simple phoneme sequence using a basic English-to-phoneme lookup table (hardcoded dictionary, 100-200 common words).
  - Map emphasis to volume: none=0.5, soft=0.3, loud=0.8, shout=1.0.
  - Map sustain to vibrato=True and duration_modifier applied to duration_ms.
  - Map harmony to harmony_intervals=[4, 7] (major chord).
  - Assign sequential start_ms based on cumulative duration.
  - Default pitch_hz = 220.0 (A3), adjust +-20% for emphasis.

- Concrete class `LlamaLLMProcessor(LLMProcessor)` (stub for now):
  - Constructor takes model path.
  - `process()` raises `NotImplementedError("Llama integration pending")`.
  - Add `llama-cpp-python` to `pyproject.toml` optional dependencies: `llm-local`.

- Concrete class `ClaudeLLMProcessor(LLMProcessor)` (stub for now):
  - Constructor takes API key.
  - `process()` raises `NotImplementedError("Claude integration pending")`.
  - Add `anthropic` to `pyproject.toml` optional dependencies: `llm-cloud`.

**Tests (`tests/test_llm_processor.py`):**

- MockLLMProcessor converts a simple token list into PhonemeEvents.
- Loud emphasis -> volume > 0.7.
- Soft emphasis -> breathiness > 0.5, volume < 0.4.
- Sustain -> vibrato = True, longer duration_ms.
- Harmony -> harmony_intervals is non-empty.
- Output events have sequential, non-overlapping start_ms values.

### Step 1.5 -- Output Buffer

**File:** `mavis/output_buffer.py`

Purpose: FIFO buffer of PhonemeEvents awaiting audio synthesis. Buffer level is the core game mechanic.

**What to build:**

- Dataclass `BufferState` (from spec.md Section 7.3):
  ```python
  @dataclass
  class BufferState:
      level: float         # 0.0 - 1.0
      status: str          # "underflow" | "optimal" | "overflow"
      drain_rate: float    # phonemes consumed per second
      fill_rate: float     # phonemes received per second
  ```

- Class `OutputBuffer`:
  - `capacity: int` -- Max phoneme events stored.
  - `push(events: list[PhonemeEvent])` -- Add events to queue.
  - `pop() -> PhonemeEvent | None` -- Get next event for synthesis.
  - `state() -> BufferState` -- Current fill level and status.
    - level < 0.2 -> "underflow"
    - 0.2 <= level <= 0.8 -> "optimal"
    - level > 0.8 -> "overflow"
  - `drain_rate` and `fill_rate` tracked using a sliding window (last 2 seconds of push/pop timestamps).

**Tests (`tests/test_output_buffer.py`):**

- Empty buffer state is underflow, level 0.0.
- Push events, verify level increases.
- Pop events, verify level decreases.
- Fill to capacity, verify overflow status.
- Verify drain_rate / fill_rate update after push/pop sequences.

### Step 1.6 -- Audio Synthesis

**File:** `mavis/audio.py`

Purpose: Convert PhonemeEvents into audio waveform and play to speaker.

**What to build:**

- Abstract base class `AudioSynthesizer`:
  - `synthesize(event: PhonemeEvent) -> bytes` -- Return raw PCM audio bytes.
  - `play(audio_data: bytes)` -- Play audio to speaker.

- Concrete class `MockAudioSynthesizer(AudioSynthesizer)`:
  - `synthesize()` generates a sine wave at `event.pitch_hz` for `event.duration_ms` milliseconds.
  - Apply volume scaling.
  - If vibrato, add pitch modulation (5 Hz LFO, +-10 Hz).
  - If harmony_intervals, sum sine waves at transposed pitches.
  - Return 16-bit PCM at 22050 Hz sample rate.
  - `play()` writes to stdout as a status message (no actual audio playback, for testing).

- Concrete class `EspeakSynthesizer(AudioSynthesizer)` (stub):
  - Wraps `espeak-ng` CLI via `subprocess`.
  - Raises `NotImplementedError` until espeak-ng integration is done.
  - Add `espeak-ng` to system dependency documentation.

- Concrete class `CoquiSynthesizer(AudioSynthesizer)` (stub):
  - Raises `NotImplementedError`.
  - Add `TTS` to optional dependencies: `tts-coqui`.

**Tests (`tests/test_audio.py`):**

- MockAudioSynthesizer produces bytes of correct length for a given duration.
- Volume 0.0 produces silence (all zero bytes).
- Volume 1.0 produces non-silent output.
- Vibrato flag changes the output (not identical to non-vibrato).

### Step 1.7 -- Pipeline Orchestrator

**File:** `mavis/pipeline.py`

Purpose: Wire InputBuffer -> SheetTextParser -> LLMProcessor -> OutputBuffer -> AudioSynthesizer into a single runnable pipeline.

**What to build:**

- Class `MavisPipeline`:
  - Constructor takes `MavisConfig`.
  - Instantiates all components based on config backend selections.
  - `feed(char: str, modifiers: dict)` -- Push character into input buffer.
  - `tick(elapsed_ms: int)` -- Called on each frame/update cycle:
    1. If input buffer has enough characters, consume a chunk.
    2. Parse consumed characters into Sheet Text tokens.
    3. Send tokens to LLM processor, get phoneme events.
    4. Push phoneme events into output buffer.
    5. If output buffer has events, pop one and synthesize audio.
  - `state() -> dict` -- Return combined state: input buffer level, output buffer state, last phoneme played.

- Function `create_pipeline(config: MavisConfig) -> MavisPipeline` -- Factory function.

**Tests (`tests/test_pipeline.py`):**

- Create pipeline with all-mock backends.
- Feed characters for `"the SUN rises"`.
- Call `tick()` repeatedly.
- Verify output buffer receives phoneme events.
- Verify state() returns reasonable values at each step.

### Step 1.8 -- Demo: Pipeline Visualization

**File:** `demos/vocal_typing_demo.py`

Purpose: Non-interactive demonstration. Feeds a hardcoded Sheet Text string through the pipeline and prints buffer states and phoneme events to the terminal.

**What to build:**

- Hardcoded input: `"the SUN... is falling _down_ and RISING [again]"`
- Create pipeline with mock backends and LAPTOP_CPU profile.
- Simulate keystrokes at 60 WPM (one character every 200ms).
- On each tick, print:
  - Input buffer level bar: `[████░░░░░░]`
  - Current Sheet Text token being processed.
  - Phoneme event being synthesized.
  - Output buffer level bar and status.
- Sleep between ticks to show real-time flow.

### Step 1.9 -- Demo: Interactive Typing

**File:** `demos/interactive_vocal_typing.py`

Purpose: User types Sheet Text in the terminal; the pipeline processes it and shows buffer visualizations live.

**What to build:**

- Use a library for non-blocking keyboard input. Options:
  - `curses` (stdlib, Linux/macOS) -- preferred for Phase 1.
  - `pynput` -- cross-platform but adds a dependency.
- Main loop:
  - Read keystrokes with modifier detection (shift, ctrl, alt).
  - Feed each keystroke to `MavisPipeline.feed()`.
  - Call `pipeline.tick()` on each frame (target 30 FPS = tick every 33ms).
  - Render buffer visualizations using curses.
  - Show the "score" of the current performance (see Step 1.10).
- Handle exit on `Esc` or `Ctrl+C`.

### Step 1.10 -- Scoring System

**File:** `mavis/scoring.py`

Purpose: Track performance quality based on buffer management and markup accuracy.

**What to build:**

- Class `ScoreTracker`:
  - `on_tick(buffer_state: BufferState)` -- Called each frame.
    - Award points for time spent in "optimal" zone.
    - Penalize for time in "underflow" or "overflow".
  - `on_token(token: SheetTextToken, expected: SheetTextToken | None)` -- Compare typed token against expected song token (if playing a song).
    - Accuracy bonus for matching emphasis, sustain, harmony.
  - `score() -> int` -- Current total score.
  - `grade() -> str` -- Letter grade: S / A / B / C / D / F based on score thresholds.

**Tests (`tests/test_scoring.py`):**

- Continuous optimal buffer -> high score.
- Continuous underflow -> low score.
- Correct markup matching -> bonus points.

### Step 1.11 -- First Song

**File:** `songs/twinkle.json`

Purpose: One playable song to validate the full pipeline.

**Format:**
```json
{
  "title": "Twinkle Twinkle Little Star",
  "bpm": 90,
  "difficulty": "easy",
  "sheet_text": "TWINKLE twinkle _little_ STAR...\nhow I WONDER... what you ARE...",
  "tokens": [
    {"text": "TWINKLE", "emphasis": "loud", "sustain": false, "harmony": false, "duration_modifier": 1.0},
    ...
  ]
}
```

- The `tokens` array is the "expected" sequence for scoring.
- The `sheet_text` is what the player sees on screen.

**Song loader** in `mavis/songs.py`:
- `load_song(path: str) -> Song` -- Parse JSON into a Song dataclass.
- `Song` holds title, bpm, difficulty, sheet_text, and expected token list.

### Step 1.12 -- Visual Sustain Bars

Add to the interactive demo (Step 1.9):

- When the player holds a sustain (`...`), render a horizontal bar that grows while the key is held.
- Bar color indicates quality:
  - Green: held for the right duration.
  - Yellow: slightly off.
  - Red: too short or too long.
- Render using curses character blocks (`█`, `▓`, `░`).

### Phase 1 Completion Checklist

- [ ] `mavis/` package imports cleanly.
- [ ] All tests pass: `python -m pytest tests/ -v`.
- [ ] `demos/vocal_typing_demo.py` runs and shows buffer flow.
- [ ] `demos/interactive_vocal_typing.py` accepts typing and shows live buffers.
- [ ] `songs/twinkle.json` loads and is playable in interactive mode.
- [ ] Scoring displays at end of song.

---

## Phase 2: Game Polish

Build on the working alpha to make it feel like a real game.

### Step 2.1 -- Song Library

**Directory:** `songs/`

Create 10 songs across 3 difficulty tiers.

| # | Song | Difficulty | Key Markups |
|---|------|-----------|-------------|
| 1 | Twinkle Twinkle (exists) | Easy | CAPS, `_soft_` |
| 2 | Mary Had a Little Lamb | Easy | CAPS only |
| 3 | Row Row Row Your Boat | Easy | `...` sustain |
| 4 | Amazing Grace | Medium | CAPS, `_soft_`, `...` |
| 5 | Hallelujah (Cohen) | Medium | All markups |
| 6 | Bohemian Rhapsody (excerpt) | Medium | `[harmony]`, dynamics |
| 7 | Somewhere Over the Rainbow | Medium | `_soft_`, `...` |
| 8 | Don't Stop Believin' (excerpt) | Hard | Fast CAPS transitions |
| 9 | Nessun Dorma (excerpt) | Hard | Full range, sustains |
| 10 | Rap God (excerpt) | Hard | Speed, no sustain |

**What to build:**

- Create each song as a `.json` file in `songs/`.
- Add `mavis/song_browser.py`: list available songs, filter by difficulty, display song metadata.
- Add a song selection screen to the interactive demo before gameplay starts.

### Step 2.2 -- Difficulty Levels

**File:** `mavis/difficulty.py`

Map difficulty levels to concrete gameplay parameters.

| Parameter | Easy | Medium | Hard |
|-----------|------|--------|------|
| Buffer window (s) | 5.0 | 2.5 | 1.0 |
| Markup tolerance | Ignore wrong emphasis | Partial penalty | Full penalty |
| Timing strictness | +/- 500ms | +/- 200ms | +/- 50ms |
| Song speed multiplier | 0.75x | 1.0x | 1.25x |

- Class `DifficultySettings`:
  - `buffer_window_s: float`
  - `markup_tolerance: str` ("lenient" | "partial" | "strict")
  - `timing_tolerance_ms: int`
  - `speed_multiplier: float`

- Player can choose difficulty before each song.
- Update `MavisPipeline` and `ScoreTracker` to use `DifficultySettings`.

### Step 2.3 -- Leaderboards

**File:** `mavis/leaderboard.py`

Local-only leaderboard stored in a JSON file.

**What to build:**

- Storage file: `~/.mavis/leaderboards.json`
- Structure:
  ```json
  {
    "twinkle": [
      {"name": "Player1", "score": 9500, "grade": "S", "difficulty": "hard", "date": "2026-02-05"}
    ]
  }
  ```
- Class `Leaderboard`:
  - `submit(song_id: str, name: str, score: int, grade: str, difficulty: str)`
  - `top(song_id: str, n: int = 10) -> list[dict]`
  - `personal_best(song_id: str, name: str) -> dict | None`
- Display top 10 after each song in the interactive demo.

### Step 2.4 -- Voice Customization

**File:** `mavis/voice.py`

Allow the player to adjust vocal characteristics.

**Parameters:**

| Setting | Range | Default | Effect |
|---------|-------|---------|--------|
| Base pitch | 80 - 400 Hz | 220 Hz | Fundamental frequency |
| Voice type | bass / tenor / alto / soprano | tenor | Preset pitch + formant |
| Vibrato rate | 3 - 8 Hz | 5 Hz | LFO speed on sustain |
| Vibrato depth | 0 - 30 Hz | 10 Hz | LFO amplitude |
| Breathiness | 0.0 - 1.0 | 0.2 | Noise mix in soft passages |

- Class `VoiceProfile`:
  - Store all settings.
  - Serialize/deserialize to `~/.mavis/voice.json`.
- Pass `VoiceProfile` to `AudioSynthesizer` to modulate all output.
- Add a voice settings screen to the interactive demo.

### Step 2.5 -- Tutorial Mode

**File:** `mavis/tutorial.py`

Guided introduction for new players.

**Sequence:**

1. **Lesson 1: Basic typing** -- Type plain text, see buffer fill/drain. No markup.
2. **Lesson 2: Emphasis** -- Introduce CAPS for loud. Type `"the SUN rises"`.
3. **Lesson 3: Soft voice** -- Introduce `_underscores_`. Type `"falling _gently_ down"`.
4. **Lesson 4: Sustain** -- Introduce `...`. Type `"hold... this... note..."`.
5. **Lesson 5: Harmony** -- Introduce `[brackets]` / Ctrl. Type `"singing [together]"`.
6. **Lesson 6: Full performance** -- Combine all markups in a short passage.
7. **Lesson 7: Buffer management** -- Explain optimal zone. Practice speed control.

Each lesson:
- Shows instructions on screen.
- Highlights the expected keystrokes.
- Gives real-time feedback ("Too fast!", "Nice emphasis!", "Hold longer...").
- Must score C or above to advance.

### Phase 2 Completion Checklist

- [ ] 10 songs in `songs/` directory, all loadable.
- [ ] Song browser lists songs, shows difficulty, allows selection.
- [ ] Three difficulty levels affect gameplay parameters.
- [ ] Leaderboard saves and displays scores locally.
- [ ] Voice customization persists between sessions.
- [ ] Tutorial walks new player through all 7 lessons.

---

## Phase 3: Platform Launch

Expand from a terminal application to web, mobile, and connected platforms.

### Step 3.1 -- Web Version

**Directory:** `web/`

Browser-based client that communicates with a Python backend.

**Architecture:**

```
Browser (JS/HTML) <--WebSocket--> Python Server (FastAPI) <--> MavisPipeline
```

**Backend (`web/server.py`):**

- FastAPI application with WebSocket endpoint.
- On WebSocket connect: create a `MavisPipeline` instance for the session.
- On message (keystroke): call `pipeline.feed()`, then `pipeline.tick()`, return state as JSON.
- Endpoint `GET /songs` -- list available songs.
- Endpoint `GET /songs/{id}` -- get song details.
- Endpoint `GET /leaderboard/{song_id}` -- get top scores.
- Endpoint `POST /leaderboard/{song_id}` -- submit score.
- Add `fastapi`, `uvicorn`, `websockets` to `pyproject.toml` optional dependencies: `web`.

**Frontend (`web/static/`):**

- `index.html` -- Single page app.
- `app.js` -- WebSocket client.
  - Capture keyboard events with modifier detection.
  - Send keystrokes over WebSocket.
  - Receive state updates, render buffer bars (CSS animations or canvas).
  - Render Sheet Text with the current position highlighted.
  - Use Web Audio API for audio playback (receive PCM from server or synthesize client-side).
- `style.css` -- Minimal styling; buffer bars, score display, song text.

**Audio strategy options:**

- Option A: Server synthesizes audio, streams PCM over WebSocket. Higher bandwidth, simpler client.
- Option B: Server sends PhonemeEvents, client synthesizes using Web Audio API oscillators. Lower bandwidth, more client code.
- Recommendation: Start with Option A for simplicity, optimize to Option B if latency is unacceptable.

**Web Audio latency concern:**

- Browser audio output adds 20-100ms latency depending on OS and buffer size.
- `AudioContext` with small buffer sizes (256 samples) minimizes this.
- Test on Chrome, Firefox, Safari; document measured latencies.

### Step 3.2 -- Mobile Apps (iOS / Android)

**Directory:** `mobile/`

React Native application.

**Approach:**

- Use React Native with a Python backend hosted remotely (same FastAPI server from Step 3.1).
- Mobile app is a thin client: keyboard input, WebSocket communication, audio playback.
- Alternatively: bundle the Python pipeline via Chaquopy (Android) or PythonKit (iOS) for offline play.

**Key files:**

- `mobile/App.js` -- Main component.
- `mobile/src/WebSocketClient.js` -- Connection to backend.
- `mobile/src/BufferDisplay.js` -- Visual buffer bars (React Native Animated API).
- `mobile/src/SheetTextView.js` -- Song text display with active position marker.
- `mobile/src/AudioPlayer.js` -- Play audio from server stream.

**Touch input mapping:**

| Touch Gesture | Keyboard Equivalent | Effect |
|---------------|---------------------|--------|
| Tap key on virtual keyboard | Normal keypress | Standard input |
| Long press | Sustain (`...`) | Vibrato |
| Swipe up on key | Shift (CAPS) | Loud emphasis |
| Swipe down on key | `_underscore_` | Soft emphasis |
| Two-finger tap | Ctrl (`[brackets]`) | Harmony |

### Step 3.3 -- Cloud Save

**Backend addition to FastAPI server.**

**What to build:**

- User accounts: username + password (hashed with bcrypt), stored in SQLite or PostgreSQL.
- Endpoints:
  - `POST /auth/register`
  - `POST /auth/login` -- Returns JWT.
  - `GET /profile` -- User stats, voice profile, progress.
  - `PUT /profile/voice` -- Save voice settings.
  - `GET /progress` -- Tutorial completion, songs played, personal bests.
  - `PUT /progress` -- Sync progress.
- All game data synced on login: leaderboard scores, voice profile, tutorial progress, song completion.
- Offline-first: local data is the source of truth; cloud sync on connect.

**Dependencies:** `bcrypt`, `python-jose` (JWT), `sqlalchemy` (ORM).

### Step 3.4 -- Multiplayer / Duets

**What to build:**

- **Mode 1: Competitive** -- Two players play the same song simultaneously. Higher score wins.
- **Mode 2: Duet** -- Two players each get half the Sheet Text (melody + harmony). Combined audio output.

**Architecture:**

- WebSocket rooms: server creates a room ID, both players connect.
- Server runs two `MavisPipeline` instances, one per player.
- Each tick, server sends both players' buffer states and audio to both clients.
- Score comparison displayed in real time.
- For duets: server mixes both audio streams before sending.

**Key additions:**

- `mavis/multiplayer.py`:
  - Class `Room`: holds two pipelines, manages turn/sync.
  - Class `DuetSplitter`: divides a song's Sheet Text into two complementary parts.
- WebSocket protocol extension: room join/leave, opponent state broadcasts.

### Step 3.5 -- User-Generated Content

**What to build:**

- **Song editor:** Web interface for creating new songs.
  - Text area for Sheet Text with syntax highlighting.
  - Preview button: play the song through the pipeline.
  - BPM selector, difficulty rating.
  - Export to JSON format.
- **Song sharing:** Upload songs to server, browse community songs.
  - Endpoint `POST /songs/upload` (authenticated).
  - Endpoint `GET /songs/community` with pagination, sort by rating.
  - Endpoint `POST /songs/{id}/rate` -- 1-5 star rating.
- **Moderation:** Flag system for inappropriate content. Admin review queue.

### Phase 3 Completion Checklist

- [ ] Web version works in Chrome, Firefox, Safari.
- [ ] Mobile app runs on iOS and Android (or at minimum a working React Native prototype).
- [ ] Cloud save syncs user data across devices.
- [ ] Multiplayer competitive mode supports 2 players.
- [ ] Duet mode splits songs and mixes audio.
- [ ] Song editor creates valid song JSON files.
- [ ] Community song sharing with upload/browse/rate.

---

## Phase 4: Ecosystem Integration

Connect Mavis to the broader Natural Language Ecosystem projects.

### Step 4.1 -- Prosody-Protocol Export (IMPLEMENTED)

**File:** `mavis/export.py` -- **Already built during Phase 1.**

**Reference:** [Prosody-Protocol repo](https://github.com/kase1111-hash/Prosody-Protocol)

Every performance generates data conforming to the Prosody-Protocol's IML specification and `dataset-entry.schema.json`. The export module (`mavis/export.py`) already provides:

- `PerformanceRecording` -- records keystrokes, tokens, phonemes, and buffer states with ms timestamps.
- `tokens_to_iml()` / `phoneme_events_to_iml()` -- generate IML 1.0 XML with `<prosody>`, `<emphasis>`, `<pause>` tags.
- `recording_to_dataset_entry()` -- produces dataset entry JSON with `source="mavis"`, IML markup, emotion label, consent flag.
- `export_performance()` / `export_dataset()` -- write individual or batch entries to disk.
- `extract_training_features()` -- 7-dim feature vector matching `MavisBridge.extract_training_features()`.
- `infer_emotion()` -- heuristic emotion classification (neutral/angry/joyful/sad/calm).

**Pipeline integration:** `MavisPipeline.start_recording()` / `stop_recording()` enable opt-in recording of full sessions.

**Remaining work for Phase 4:**
- Wire export into the interactive demo UI (export button / auto-export on song completion).
- Add audio file generation alongside dataset entries (currently empty string).
- Validate output against `prosody_protocol.IMLValidator` when the SDK is installed.
- Bulk export to JSONL for ML training pipelines.

### Step 4.2 -- Intent-Engine Integration

**File:** `mavis/intent_bridge.py`

Connect to the intent-engine project to enable prosody-aware AI processing of performances.

**What to build:**

- Class `IntentBridge`:
  - `analyze(performance_data: dict) -> dict` -- Send a performance recording to intent-engine, receive prosody intent analysis.
  - Example output: `{"dominant_emotion": "triumph", "energy_curve": [0.3, 0.5, 0.9, 0.7], "intent_confidence": 0.85}`
- Use this to:
  - Generate post-performance feedback ("Your performance conveyed increasing energy and a triumphant climax").
  - Provide coaching suggestions ("Try softer dynamics in bar 3 for more contrast").
  - Classify performances for the training dataset.
- Communication: HTTP REST calls to intent-engine service.
- Fallback: if intent-engine is unavailable, skip analysis without breaking gameplay.

### Step 4.3 -- Researcher API

**Backend addition to FastAPI server.**

Provide a public API for researchers to access anonymized performance data.

**Endpoints:**

- `GET /api/v1/performances` -- Paginated list of anonymized performances (with consent).
  - Query params: `song_id`, `difficulty`, `min_score`, `limit`, `offset`.
- `GET /api/v1/performances/{id}` -- Full performance event stream.
- `GET /api/v1/statistics` -- Aggregate stats: total performances, average scores by song, markup usage frequencies.
- `GET /api/v1/prosody-map` -- Aggregated text-to-prosody mappings across all performances.

**Access control:**

- API key required (register at `/api/v1/register`).
- Rate limiting: 100 requests/minute.
- Data is anonymized: no player names, no raw keystrokes (only tokens and phonemes).

**Documentation:**

- OpenAPI spec auto-generated by FastAPI.
- Usage guide in `docs/api.md`.

### Step 4.4 -- Institutional Licensing

**File:** `mavis/licensing.py`

Support deployment in therapy, education, and research institutions.

**What to build:**

- License tiers:
  - **Free:** Personal use, all core features, local only.
  - **Institutional:** Cloud features, multiplayer, researcher API access, priority support.
  - **Research:** Full data export, bulk API access, custom song library hosting.
- License key validation:
  - Check key against server on startup (with offline grace period).
  - Feature gating based on tier.
- Admin dashboard (web):
  - Manage users within institution.
  - View aggregate usage statistics.
  - Configure custom song libraries.
  - Export usage reports.

### Phase 4 Completion Checklist

- [ ] Performance recording captures full event stream.
- [ ] Export produces valid prosody-protocol JSON/JSONL.
- [ ] Intent-engine integration returns emotion/intent analysis.
- [ ] Researcher API serves anonymized data with rate limiting.
- [ ] License key system gates features by tier.
- [ ] Admin dashboard manages institutional deployments.

---

## Implementation Order Summary

This is the recommended order for building Mavis from zero to full ecosystem:

```
Phase 0: Scaffolding
  0.1  pyproject.toml + mavis/ package
  0.2  Test infrastructure
  0.3  Placeholder demos

Phase 1: Playable Alpha
  1.1  Input Buffer
  1.2  Sheet Text Parser
  1.3  Config / Hardware Profiles
  1.4  LLM Phoneme Processor (mock + stubs)
  1.5  Output Buffer
  1.6  Audio Synthesis (mock + stubs)
  1.7  Pipeline Orchestrator
  1.8  Demo: pipeline visualization
  1.9  Demo: interactive typing
  1.10 Scoring system
  1.11 First song (Twinkle Twinkle)
  1.12 Visual sustain bars

Phase 2: Game Polish
  2.1  Song library (10 songs)
  2.2  Difficulty levels
  2.3  Leaderboards (local)
  2.4  Voice customization
  2.5  Tutorial mode (7 lessons)

Phase 3: Platform Launch
  3.1  Web version (FastAPI + WebSocket + static frontend)
  3.2  Mobile apps (React Native)
  3.3  Cloud save (auth + sync)
  3.4  Multiplayer / duets
  3.5  User-generated content (editor + sharing)

Phase 4: Ecosystem Integration
  4.1  Prosody-protocol export
  4.2  Intent-engine integration
  4.3  Researcher API
  4.4  Institutional licensing
```

Each step is designed to be independently testable and to build on the previous step. Complete all tests before moving to the next step.

# PROJECT EVALUATION REPORT

**Primary Classification:** Feature Creep
**Secondary Tags:** Multiple Ideas in One

---

## CONCEPT ASSESSMENT

**Problem solved:** Lowering the barrier to musical expression by converting a universal skill (typing) into vocal performance through prosody-annotated text ("Sheet Text"). Secondary goal: generating labeled prosody training data for ML pipelines via the Prosody-Protocol ecosystem.

**User:** Three stated audiences: (1) casual users / office workers who want to "discover they're already musicians," (2) accessibility users who type via adaptive interfaces and want vocal expression, (3) AI researchers who need prosody-annotated training data.

**Competition:** Rhythm games (Guitar Hero, Osu!, Rocksmith) own the "gamified music performance" space. Typing-to-singing specifically appears to have no direct competitor. However, the actual value delivered -- hearing your typing as music -- requires functional audio synthesis, which this project does not have.

**Value prop in one sentence:** Your keyboard is already a musical instrument; Mavis adds the sound card.

**Verdict:** Sound -- with a caveat.

The core insight is genuine: typing already has rhythm, dynamics, and phrasing. Mapping markup like CAPS=loud, `_underscores_`=soft, `...`=sustain onto a vocal synthesis pipeline is a legitimate and original idea. The accessibility angle (eye-tracking, sip-puff, adaptive keyboards → singing) is compelling and underserved.

The caveat: the concept's validity hinges entirely on the audio output quality. If the synthesized voice sounds bad, the product fails regardless of how clean the pipeline architecture is. The concept is sound in theory but unvalidated in practice because no real audio synthesis exists. Every feature built on top of "what if the singing sounds good" is speculative until that question is answered.

---

## EXECUTION ASSESSMENT

### Architecture

Clean layered design. Zero circular imports across 21 modules. Average module size is ~184 lines, with the largest (`export.py` at 490 lines) justified by scope. The pipeline orchestrator (`mavis/pipeline.py:21-181`) follows a clear 5-step tick cycle: consume input → parse Sheet Text → LLM process → voice profile → synthesize. Composition pattern throughout -- `MavisPipeline` composes `InputBuffer`, `OutputBuffer`, `LLMProcessor`, `AudioSynthesizer`. Factory functions (`create_pipeline()`, `_create_llm()`, `_create_audio()`) make backend swapping straightforward.

The architecture is genuinely good. It was designed for extensibility and achieves it.

### Code Quality

Consistent `@dataclass` usage for all data models. Type hints on ~80% of signatures. Shared `storage.py` module for atomic JSON I/O with file locking. Proper abstract base classes for LLM and audio backends. Error handling follows consistent `{"error": "message"}` patterns in the web layer.

315 tests pass across 23 test files, including 27 web endpoint tests (REST + WebSocket). Test-to-code ratio is ~76%. Shared fixtures in `conftest.py`. Parametric testing for difficulty presets and voice profiles.

### The Core Problem

Despite all this, the two components that make the product work -- the LLM and the TTS -- are mocks:

- `MockLLMProcessor` (`mavis/llm_processor.py:101-142`): A 60-word English-to-IPA dictionary. Does not use any LLM. Maps emphasis to volume/pitch multipliers. This is a lookup table, not language processing.
- `MockAudioSynthesizer` (`mavis/audio.py:25-70`): Generates sine waves at 22050 Hz. Supports vibrato (5 Hz LFO) and harmony intervals. `play()` is a no-op that produces no audible output.
- `LlamaLLMProcessor` and `ClaudeLLMProcessor`: Both raise `NotImplementedError` (`mavis/llm_processor.py:145-162`).
- `EspeakSynthesizer` and `CoquiSynthesizer`: Both raise `NotImplementedError` (`mavis/audio.py:73-91`).

The product's entire value proposition -- hearing singing from typing -- is unimplemented. Everything else (scoring, leaderboards, multiplayer, cloud save, licensing, researcher API) is scaffolding around an empty core.

### Tech Choices

Python 3.8+, FastAPI, pytest -- appropriate and well-chosen. `pyproject.toml` with optional dependency groups is clean packaging. The dependency structure (mock defaults with optional real backends) is the right approach. No issues here.

### Security

- Password hashing in `cloud.py:112-120`: Falls back to iterated SHA-256 when bcrypt is unavailable. The iteration count (100k rounds HMAC) is reasonable for a fallback but SHA-256 is not memory-hard, making GPU attacks viable.
- Token generation in `cloud.py:78-88`: HMAC-style with 64-bit truncated SHA-256 signature. Not JWT. Tokens contain plaintext user_id and expiry.
- Hardcoded secret fallbacks: `cloud.py:75` (`"mavis-dev-secret"`) and `licensing.py:88` (`"mavis-dev-secret-key"`). Both emit warnings but don't refuse to start. A production deployment that forgets to set env vars silently runs with known secrets.
- CORS allows `*` methods and `*` headers (`web/server.py:57-65`). No CSRF protection.

These are acceptable for a proof-of-concept that states it's not production-ready. They would be unacceptable for any deployment.

### Commit History

The entire codebase was built in ~9 commits across the same branch pattern (`claude/add-documentation-files-*`), suggesting it was generated in a single AI-assisted session. Phase 1 through Phase 4 were implemented sequentially in discrete commits. This is consistent with the observed uniformity of code style and documentation quality, but also explains the breadth-over-depth pattern: it's easier to scaffold many features than to make one feature actually work.

**Verdict:** Over-engineered relative to core gap.

The architecture is professional. The code quality is above average. The test coverage is solid. But the project invested in breadth (4 phases, 21 modules, multiplayer, licensing, researcher API) while the core engine that would make the product usable remains a mock. The execution demonstrates engineering competence but misallocated priorities. A narrower project with real LLM + TTS integration and 5 modules would be more valuable than this 21-module scaffold with sine waves.

---

## SCOPE ANALYSIS

**Core Feature:** The typing-to-singing pipeline (InputBuffer → SheetText → LLM → OutputBuffer → Audio). This is the one thing that defines Mavis. Without real audio output, the product has no reason to exist.

**Supporting:**
- Sheet Text parser (`mavis/sheet_text.py`) -- directly enables the core prosody markup
- Buffer management mechanic (`mavis/input_buffer.py`, `mavis/output_buffer.py`) -- the gameplay loop
- Scoring system (`mavis/scoring.py`) -- gamifies the core loop
- Song loader and library (`mavis/songs.py`, `songs/`) -- provides content for the core loop

**Nice-to-Have:**
- Difficulty presets (`mavis/difficulty.py`) -- 4 presets, 118 lines. Useful but could be hardcoded initially
- Voice profiles (`mavis/voice.py`) -- 6 presets. Meaningless without real TTS to hear the difference
- Tutorial system (`mavis/tutorial.py`) -- 7 lessons, 224 lines. Valuable for onboarding but premature before core works
- Leaderboards (`mavis/leaderboard.py`) -- Local JSON storage. Fine for polish phase
- Song browser (`mavis/song_browser.py`) -- Terminal formatting. Low effort, fine to keep

**Distractions:**
- Cloud save system (`mavis/cloud.py`, 261 lines) -- User accounts, password hashing, sync logic, offline-first merge. This is infrastructure for a platform that doesn't have a working product yet.
- Multiplayer (`mavis/multiplayer.py`, 285 lines) -- 2-player rooms, duet splitting, competitive modes. Multiplayer for a product that can't produce audio.
- User-generated content (`mavis/song_editor.py`, 253 lines) -- Song creation, community library with ratings and moderation. UGC for a community that doesn't exist.
- Mobile client (`mobile/`, ~4 files) -- React Native thin client. A second frontend before the first one delivers value.
- Web frontend (`web/static/`, 7 screens) -- SPA with multiplayer lobby, settings, song browser. Over-scoped UI for a proof-of-concept.
- FastAPI server routers (`web/routers/`, 3 files) -- Auth, songs, researcher endpoints. Server infrastructure for a local-first tool.

**Wrong Product:**
- Researcher API (`mavis/researcher_api.py`, 356 lines) -- Anonymized performance storage, API key management with HMAC hashing, sliding-window rate limiting, statistics aggregation, prosody feature mapping. This is a **data platform** product, not a musical instrument feature.
- Institutional licensing (`mavis/licensing.py`, 330 lines) -- 3-tier licensing with HMAC-SHA256 signed keys, feature gating, offline grace periods, license management. This is a **business/monetization** product. Building licensing before having a single paying user (or a working product) is premature.
- Intent-engine bridge (`mavis/intent_bridge.py`, 297 lines) -- REST client for a separate prosody analysis service, local heuristic fallback, coaching suggestions. This is a **platform integration** product that assumes an ecosystem that doesn't exist yet.
- Prosody-Protocol IML export (`mavis/export.py`, 490 lines, the largest module) -- IML XML generation, JSONL bulk export, 7-dimensional feature vectors, emotion inference, WAV generation, dataset directory creation. The export module is bigger than the pipeline it's exporting from. This is a **data pipeline** product.

**Scope Verdict:** Feature Creep bordering on Multiple Products.

The project contains at least three distinct products:
1. **Mavis the Instrument** -- typing-to-singing pipeline with game mechanics (the stated product)
2. **Mavis the Data Platform** -- researcher API, anonymized storage, IML/JSONL export, feature vectors (a research infrastructure product)
3. **Mavis the SaaS Platform** -- cloud accounts, multiplayer, UGC, licensing tiers, mobile app (a platform business product)

Products 2 and 3 were built before Product 1 works. The instrument can't sing, but it can manage your license key and export your non-existent performance data in two formats.

---

## RECOMMENDATIONS

**CUT:**
- `mavis/licensing.py` (330 lines) -- No users, no revenue, no product. Licensing a free proof-of-concept is absurd. Delete entirely.
- `mavis/researcher_api.py` (356 lines) -- No researchers, no data worth researching (mock sine waves), no ecosystem. Delete or move to a separate repo.
- `mavis/intent_bridge.py` (297 lines) -- Bridges to a service that doesn't exist in this context. The local heuristic fallback is 6 emotion labels derived from volume/pitch thresholds -- not worth 297 lines. Delete.
- `mobile/` (entire directory) -- React Native client for a product that doesn't produce audio. A second frontend before the first delivers value. Delete.
- `web/routers/researcher.py` -- Endpoints for the researcher API above. Delete with it.
- License endpoints in `web/server.py` -- Delete with licensing module.

**DEFER:**
- `mavis/cloud.py` (261 lines) -- Cloud sync, user accounts, auth. Defer until the product has users. Local-only is fine for a proof-of-concept.
- `mavis/multiplayer.py` (285 lines) -- Competitive and duet modes. Defer until single-player works and sounds good.
- `mavis/song_editor.py` (253 lines) -- UGC and community library. Defer until there's a community.
- `mavis/export.py` bulk export features (JSONL, WAV generation, dataset directories) -- Keep `tokens_to_iml()` and `phoneme_events_to_iml()` for the IML core, defer the rest.
- `web/static/` multiplayer and settings screens -- Defer until core gameplay works in browser.

**DOUBLE DOWN:**
- **Real TTS integration.** `EspeakSynthesizer` and `CoquiSynthesizer` are empty stubs. Even espeak-ng (robotic but functional) would prove the concept produces audible singing. This is the single highest-value work item. Without it, Mavis is a typing game that claims to sing but doesn't.
- **Real LLM integration.** `LlamaLLMProcessor` is a stub. Even a small local model (Phi-3, Llama 3B) doing text-to-phoneme conversion would validate that the pipeline architecture works end-to-end with real AI processing.
- **Audio output in the demo.** `MockAudioSynthesizer.play()` is a no-op (`mavis/audio.py:68-70`). The interactive demo (`demos/interactive_vocal_typing.py`) shows buffer bars but plays no sound. Making the demo actually produce sound (even with sine waves via `pyaudio` or similar) would make the concept tangible.
- **The core pipeline.** `mavis/pipeline.py` is 213 lines of well-structured orchestration. It deserves real backends to orchestrate. Every hour spent here is worth more than the 330 lines of licensing logic.

**FINAL VERDICT:** Refocus.

The concept is sound. The architecture is solid. The engineering skill is clearly present. But the project built a four-story building on a foundation that hasn't been poured yet. The immediate path forward is to stop adding features and start making the product do the one thing it promises: turn typing into singing you can hear.

**Next Step:** Implement `EspeakSynthesizer` in `mavis/audio.py` using `espeak-ng` subprocess calls. Get the interactive demo to produce audible speech with prosody variation. This alone would transform Mavis from a well-documented typing game into a proof-of-concept that actually proves its concept.

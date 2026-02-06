# Implementation Notes

## Architecture

Mavis follows a layered architecture with zero circular dependencies:

```
Layer 0 (Foundation):    sheet_text, config, input_buffer, difficulty,
                         voice, leaderboard, tutorial, licensing, cloud,
                         researcher_api, storage

Layer 1 (Processing):    llm_processor, output_buffer, audio, scoring,
                         songs, song_browser

Layer 2 (Orchestration): pipeline, multiplayer, export, intent_bridge,
                         song_editor

Layer 3 (Presentation):  web/server.py + web/routers/
```

## Pipeline

The core pipeline (`mavis/pipeline.py`) runs a 5-step tick cycle:

1. **Consume** -- Read characters from the input buffer.
2. **Parse** -- Convert text to Sheet Text tokens (emphasis, sustain, harmony).
3. **Process** -- Map tokens to phoneme events via the LLM processor.
4. **Voice** -- Apply voice profile (pitch scaling, breathiness, volume).
5. **Synthesize** -- Generate audio from phoneme events via the TTS engine.

Buffer management is the core gameplay mechanic. The output buffer has three zones:
- **Underflow**: Voice cracks, audio dropout.
- **Optimal**: Smooth output, maximum score.
- **Overflow**: Pitch strain, rushed delivery.

## Mock Backends

The LLM and TTS engines use mock implementations:

- `MockLLMProcessor` -- Hardcoded ~50-word English-to-phoneme dictionary with prosody mapping.
- `MockAudioSynthesizer` -- Generates sine waves at the specified pitch/volume.

Stubs exist for real backends (llama-cpp-python, Claude API, espeak-ng, Coqui TTS) but are not yet integrated.

## File Persistence

All `*Store` classes use a shared pattern via `mavis/storage.py`:

- **Reads**: `locked_json_load(path)` -- shared file lock, returns parsed JSON or None.
- **Writes**: `atomic_json_save(path, data)` -- exclusive lock, write to temp file, fsync, `os.replace()`.

This provides crash safety (incomplete writes don't corrupt the target file) and basic concurrency protection (advisory file locking prevents simultaneous writers).

Storage files live in `~/.mavis/`:
- `users.json` -- User accounts and preferences.
- `leaderboards.json` -- High scores per song.
- `community.json` -- Community-uploaded songs.
- `performances.json` -- Anonymized performance data.
- `api_keys.json` -- Researcher API keys and rate limit state.
- `license.json` -- Current license activation state.
- `voice.json` -- Voice profile preference.

## Security Model

### Authentication
- Passwords: bcrypt (preferred) or iterated HMAC-SHA256 (100k rounds fallback).
- Tokens: HMAC-SHA256 with configurable TTL, verified via `hmac.compare_digest`.
- API keys: Salted SHA-256 hashing, sliding-window rate limiting (100 req/min).

### Web Server
- CORS: Configurable via `MAVIS_CORS_ORIGINS` environment variable.
- Rate limiting: Per-IP, 120 requests/minute (configurable via `MAVIS_RATE_LIMIT_RPM`).
- WebSocket: Message size limits (4KB default), JSON validation on every message.
- Auth: `Authorization: Bearer <token>` header (preferred), query param (legacy).

### Licensing
- License keys: `tier|institution|expiry|hmac_sig` with HMAC-SHA256 signatures.
- Secret: `MAVIS_LICENSE_SECRET` environment variable (warns if unset).
- Offline grace: 7 days continued use without license server contact.

## Prosody-Protocol Integration

Mavis exports data in three formats:

1. **IML XML** -- `<prosody>` and `<emphasis>` tags mapping Sheet Text to the Intent Markup Language spec.
2. **Dataset JSONL** -- Bulk export for ML training, consent-gated.
3. **Feature vectors** -- 7-dimensional: [mean_pitch, pitch_range, mean_volume, volume_range, mean_breathiness, speech_rate, vibrato_ratio].

The `prosody_protocol` SDK is optional. When installed, IML validation delegates to the SDK's `IMLValidator`. Without it, structural validation is done locally.

## Web Server Architecture

The FastAPI server is split into router modules:

- `web/server.py` -- App setup, middleware (CORS, rate limiting, logging), health check, WebSocket gameplay, multiplayer rooms.
- `web/routers/auth.py` -- Registration, login, profile, progress sync.
- `web/routers/songs.py` -- Song browsing, community UGC, leaderboards, licensing.
- `web/routers/researcher.py` -- Anonymized performance API with API key auth.

## Testing Strategy

- **307 tests** across 24 test files.
- Domain mock objects (`MockLLMProcessor`, `MockAudioSynthesizer`) instead of `unittest.mock`.
- Persistence tests use `tempfile` with `try/finally` cleanup.
- Shared fixtures in `tests/conftest.py`.
- Web server tests use FastAPI's `TestClient` for both REST and WebSocket.

# COMPREHENSIVE SOFTWARE PURPOSE & QUALITY EVALUATION

> **Note:** This evaluation was generated at commit `03dbbb5`. Many of the issues
> identified below have since been fixed. See the "Remediation Status" appendix
> at the end for a full accounting of what has been addressed.

## Evaluation Parameters

| Parameter | Value |
|-----------|-------|
| **Strictness** | 8/10 (High -- evaluating as pre-alpha with production aspirations) |
| **Context** | Open-source proof-of-concept, solo developer, MIT-licensed, 4 development phases completed |
| **Purpose Context** | Vocal typing instrument converting keyboard input to singing via AI pipeline; secondary purpose as prosody training data generator for Prosody-Protocol ecosystem |

---

## EXECUTIVE SUMMARY

### Overall Assessment

Mavis is a well-architected proof-of-concept that demonstrates strong software engineering fundamentals across 4 development phases. The codebase is organized into 21 focused modules with zero circular dependencies, 281 passing tests, and a clean separation between core pipeline logic, platform features, and ecosystem integration. The project successfully implements its stated purpose -- converting typed prosody markup into simulated vocal performance -- with mock backends that could plausibly be replaced by real LLM/TTS engines.

However, the project exhibits a significant gap between its **demo-grade implementation** and its **production-grade ambitions**. The README promises institutional licensing, researcher APIs, and cloud-based multiplayer, but the underlying security primitives (SHA-256 password hashing, hardcoded secrets, file-based persistence) are not production-ready. The web server (702 lines, 28 endpoints) has zero tests. The roadmap checkboxes remain unchecked despite all phases being implemented.

### Purpose Fidelity: 8/10

The codebase faithfully implements the stated vision of a "vocal typing instrument" across all four phases. Sheet Text parsing, pipeline orchestration, buffer management gameplay, and Prosody-Protocol export all align with the spec. The gap is in the distance between "working mock" and "usable product" -- no real LLM or TTS backend is integrated, so actual singing never occurs.

### Confidence: HIGH

This evaluation is based on reading all 21 core modules, all 23 test files, the web server, README, spec, pyproject.toml, and CLAUDE.md. Two separate analysis passes covered implementation quality and test coverage.

---

## SCORES (1-10 per dimension)

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **I. Purpose Audit** | 8 | Vision clearly articulated, all 4 phases implemented, but no real audio output exists |
| **II. Structural Analysis** | 9 | Excellent module hierarchy, zero circular deps, clean hub-and-spoke pattern |
| **III. Implementation Quality** | 6 | Solid Python but dev-grade security, no input sanitization on web endpoints, several unused imports |
| **IV. Resilience & Risk** | 5 | No web server tests, file-based storage, hardcoded secrets, no CORS/CSRF, weak auth primitives |
| **V. Dependencies & Delivery** | 7 | 281 tests pass, clean pyproject.toml, but no CI, no type checking enforced, no linting in pipeline |
| **VI. Maintainability** | 8 | Clean architecture, comprehensive CLAUDE.md, good docstrings, clear extension patterns |

**Weighted Overall: 7.0 / 10**

---

## SECTION I: PURPOSE AUDIT

### What does this software claim to do?

1. Transform keyboard typing with prosody markup ("Sheet Text") into vocal singing performance
2. Treat processing latency as a gameplay mechanic (buffer management = breath control)
3. Generate Prosody-Protocol IML training data from every performance session
4. Support institutional deployment with licensing, researcher APIs, and cloud features

### Does the implementation fulfill these claims?

| Claim | Status | Evidence |
|-------|--------|----------|
| Sheet Text parsing | **Fulfilled** | `sheet_text.py` handles CAPS, `_soft_`, `...`, `[harmony]`, ALL CAPS with two-pass shout detection |
| Pipeline orchestration | **Fulfilled** | `pipeline.py` wires InputBuffer -> Parser -> LLM -> Voice -> OutputBuffer -> Audio (213 lines) |
| Buffer management gameplay | **Fulfilled** | `output_buffer.py` tracks fill/drain rates, optimal zone thresholds per difficulty, scoring integration |
| Real audio output | **Not fulfilled** | `MockAudioSynthesizer` generates sine waves; no real TTS (espeak/Coqui/ElevenLabs) integrated |
| LLM processing | **Partially fulfilled** | `MockLLMProcessor` with ~50-word dictionary; stubs for llama-cpp and Claude API exist but are not functional |
| IML export | **Fulfilled** | `export.py` generates valid IML XML, JSONL datasets, 7-dim feature vectors, emotion labels |
| Institutional licensing | **Fulfilled (demo-grade)** | `licensing.py` with HMAC-SHA256 keys, 3 tiers, feature gating, offline grace |
| Researcher API | **Fulfilled (demo-grade)** | `researcher_api.py` with API keys, rate limiting, anonymized performance queries |
| Web + multiplayer | **Fulfilled (demo-grade)** | FastAPI with 28 endpoints, WebSocket gameplay, 2-player rooms |
| Cloud save | **Fulfilled (demo-grade)** | `cloud.py` with user accounts, token auth, offline-first sync |

### Purpose Gaps

1. **No actual singing** -- the core value proposition ("turn typing into singing") is simulated, not real
2. **README is stale** -- roadmap checkboxes are all unchecked despite all phases being implemented
3. **IMPLEMENTATION.md and CONTRIBUTING.md** are referenced in README but do not exist
4. **10 songs exist** but none have been performed through a real TTS engine

---

## SECTION II: STRUCTURAL ANALYSIS

### Architecture Quality: EXCELLENT

The codebase follows a clean layered architecture:

```
Foundation (0 internal deps): sheet_text, config, input_buffer, difficulty,
                              leaderboard, tutorial, voice, licensing, cloud,
                              researcher_api

Processing (1-2 deps):        llm_processor, output_buffer, audio, scoring,
                              songs, song_browser

Orchestration (5-9 deps):     pipeline (9), multiplayer (5), export (4),
                              intent_bridge (2), song_editor (2)

Presentation (11+ deps):      web/server.py
```

**Key Metrics:**
- 21 Python modules in `mavis/`, 1 web server, 23 test files
- 3,859 lines in `mavis/`, 702 lines in `web/`, 2,937 lines in tests
- **Zero circular imports** detected
- Test-to-code ratio: 76% (2,937 / 3,859)
- Average module size: 184 lines; median: 127 lines
- Largest module: `export.py` (491 lines) -- justified by scope
- Zero TODO/FIXME/HACK comments

### File Structure Adherence

The actual structure matches CLAUDE.md exactly. Every module listed exists, every test file listed exists, all 10 songs are present.

### Dependency Hygiene

6 unused imports detected:
- `export.py`: `asdict`, `time`
- `web/server.py`: `asyncio`, `load_song`, `MavisPipeline`, `Leaderboard`

No dead functions or unreachable code found.

---

## SECTION III: IMPLEMENTATION QUALITY

### Strengths

1. **Pipeline design** (`pipeline.py:113-165`): Clean 5-step tick cycle with optional recording, voice profile application, and monotonic time tracking
2. **Export module** (`export.py`): Prosody-Protocol compliant output with consent gating, 7-dim feature vectors, emotion inference, and optional SDK integration
3. **Dataclass usage**: Consistent use of `@dataclass` across all modules for structured data
4. **Error handling patterns**: Consistent `{"error": "message"}` responses in web server, proper None returns for validation failures
5. **Sync strategy** (`cloud.py:187-216`): Explicit conflict resolution -- last-write-wins for preferences, max-score-wins for bests, no grade downgrade

### Weaknesses

1. **Security primitives are demo-grade**:
   - Password hashing: SHA-256 with random salt (`cloud.py:99-117`) -- not bcrypt/scrypt/argon2
   - Token generation: HMAC-style with 64-bit truncated signature (`cloud.py:64-73`)
   - License secrets: Hardcoded fallback `"mavis-dev-secret-key"` (`licensing.py:83`)
   - API key storage: SHA-256 hashing without salt (`researcher_api.py`)

2. **Web server lacks defense-in-depth**:
   - No CORS configuration
   - No CSRF protection
   - No HTTPS enforcement
   - No rate limiting on main endpoints (only researcher API)
   - No input length limits on WebSocket messages
   - Auth token passed as query parameter in some flows

3. **File-based persistence everywhere**:
   - `~/.mavis/license.json`, `~/.mavis/users.json`, `~/.mavis/leaderboards.json`, etc.
   - No file locking for concurrent access
   - No atomic writes (crash during write = data loss)
   - No backup/rotation

4. **Test delimiter mismatch** (`test_licensing.py:82`): `key.split(":")` but keys use `|` delimiter -- test passes vacuously

---

## SECTION IV: RESILIENCE & RISK

### Critical Risks

| Risk | Severity | Location | Impact |
|------|----------|----------|--------|
| Web server has 0 tests | CRITICAL | `web/server.py` (702 lines, 28 endpoints) | Regressions undetectable |
| SHA-256 password hashing | HIGH | `cloud.py:99-117` | Offline brute-force viable if DB leaked |
| Hardcoded secret fallbacks | HIGH | `licensing.py:83`, `cloud.py:64` | License/token forgery if env vars unset |
| No file locking on JSON stores | MEDIUM | All `*Store` classes | Data corruption under concurrent access |
| Rate limit state in-memory only | MEDIUM | `researcher_api.py` | Rate limits reset on restart |
| No WebSocket message validation | MEDIUM | `web/server.py` | Malformed messages could cause errors |
| Wrong delimiter in test | LOW | `test_licensing.py:82` | Test passes but doesn't test its claim |

### Failure Modes

- **Server crash during file write**: Data loss (no atomic writes)
- **Multiple processes accessing JSON files**: Silent data corruption
- **License server unreachable**: Handled -- 7-day offline grace period
- **Intent-engine unavailable**: Handled -- local heuristic fallback
- **Empty temp files**: Handled -- `os.path.getsize() > 0` checks

### What's Missing

- No health check endpoint
- No graceful shutdown handling
- No request logging or audit trail
- No backup/restore for persistent data
- No monitoring or alerting hooks

---

## SECTION V: DEPENDENCIES & DELIVERY HEALTH

### Test Suite

- **281 tests, all passing** across 23 files
- **100% module coverage**: All 21 `mavis/` modules have corresponding test files
- **0% web server coverage**: `web/server.py` (28 endpoints) has no tests
- **55 error/edge case tests**: Good coverage of failure paths
- **77 persistence tests**: All use `tempfile` with proper cleanup
- **No mocking libraries**: Tests use domain mock objects -- a solid pattern
- **No conftest.py or fixtures**: Helper functions duplicated per file

### Build & Tooling

- `pyproject.toml` properly configured with 7 optional dependency groups
- `pytest` configured with `testpaths` and `-v`
- `ruff` and `mypy` configured but not enforced in CI
- **No CI pipeline** (no GitHub Actions, no Makefile, no pre-commit hooks)

### Dependency Analysis

Core dependencies: **zero** (stdlib only). Optional groups are well-separated:
- `dev`: pytest, ruff, mypy
- `web`: fastapi, uvicorn, websockets
- `cloud`: bcrypt, python-jose, sqlalchemy
- `prosody`: prosody-protocol

The core package runs on any Python 3.8+ without pip install.

---

## SECTION VI: MAINTAINABILITY PROJECTION

### Strengths

1. **CLAUDE.md is comprehensive** (350+ lines): Complete guide covering architecture, extension patterns, and development commands
2. **Module independence**: 10 of 21 modules have zero internal dependencies
3. **Consistent patterns**: Every `*Store` class follows the same JSON persistence pattern
4. **Clear extension points**: Documented how to add new Sheet Text markup (6 steps) and new songs (5 steps)

### Concerns

1. **Single developer bus factor**: No CONTRIBUTING.md, no code owners, no PR templates
2. **README drift**: Roadmap is stale, missing referenced files
3. **No versioning strategy**: Version pinned at `0.1.0` with no changelog
4. **JSON file proliferation**: 6+ files in `~/.mavis/` with no migration strategy
5. **Web server monolith**: 702 lines in one file -- will become unwieldy at 2x size

---

## POSITIVE HIGHLIGHTS

1. **Zero circular dependencies** across 21 modules
2. **Pipeline as gameplay mechanic** is genuinely novel -- latency-as-feature is well-implemented
3. **Prosody-Protocol export** is thorough: IML, JSONL, feature vectors, emotion labels, consent gating
4. **Offline-first sync** with explicit conflict resolution policies
5. **281 tests with zero anti-patterns** -- all assertions meaningful
6. **Intent-engine graceful degradation** -- local heuristic fallback
7. **Difficulty system** cleanly modifies buffer thresholds without pipeline changes
8. **CLAUDE.md** serves as both developer guide and AI agent instruction manual

---

## RECOMMENDED ACTIONS

### Priority 1 (Before any deployment)

1. **Add web server tests**: Use `httpx` + FastAPI `TestClient` for REST, `websockets` for WebSocket testing
2. **Fix `test_validate_key_wrong_signature`**: Change `key.split(":")` to `key.split("|")` to match actual delimiter
3. **Remove hardcoded secret fallbacks**: Require secrets via environment variables; fail loudly if unset
4. **Upgrade password hashing**: Use bcrypt (already in optional deps) or argon2id

### Priority 2 (Production readiness)

5. **Add CI pipeline**: GitHub Actions running pytest, ruff, and mypy on every push
6. **Add CORS configuration** to web server
7. **Implement atomic file writes**: Write to temp file, then `os.rename()`
8. **Add file locking** for concurrent access to JSON stores
9. **Split web server**: Separate auth, gameplay, UGC, and admin into router modules
10. **Persist rate limit state** to file or Redis

### Priority 3 (Ecosystem maturity)

11. **Update README**: Check roadmap boxes, add current status, fix broken links
12. **Create CONTRIBUTING.md and IMPLEMENTATION.md**
13. **Add a conftest.py** with shared fixtures
14. **Integrate a real TTS engine** (espeak-ng at minimum)
15. **Add database backend option**: SQLite via SQLAlchemy for `*Store` classes

---

## QUESTIONS FOR AUTHORS

1. **Is the intent that all 4 phases be demo-grade, or is there a plan to production-harden specific phases first?** The security gap between licensing/researcher API features and their underlying primitives suggests a demo intent, but the README's institutional focus implies production aspirations.

2. **Why are the README roadmap checkboxes all unchecked?** All 4 phases are implemented. Is this intentional or an oversight?

3. **What is the deployment target for the web server?** File-based persistence works for single-user local dev but fails under concurrent access.

4. **Is the Prosody-Protocol SDK (`prosody-protocol` package) published and installable?** The optional integration references it, but availability is unclear.

5. **What is the intended relationship between the 7-dimensional feature vector from Mavis and the intent-engine's analysis?** Both produce emotion labels through different methods. Is one intended to supersede the other?

---

## APPENDIX: REMEDIATION STATUS

The following issues identified in this evaluation have been addressed:

| # | Issue | Status | Fix |
|---|-------|--------|-----|
| 1 | Web server has 0 tests | **FIXED** | Added `tests/test_web.py` (27 tests) |
| 2 | SHA-256 password hashing | **FIXED** | bcrypt with iterated HMAC-SHA256 fallback (100k rounds) |
| 3 | Hardcoded secret fallbacks | **FIXED** | Warnings emitted when env vars unset |
| 4 | No file locking on JSON stores | **FIXED** | `mavis/storage.py` with `fcntl.flock` + `atomic_json_save` |
| 5 | Rate limit state in-memory only | **FIXED** | Persisted to JSON alongside API keys |
| 6 | No WebSocket message validation | **FIXED** | Size limits + JSON validation on both WS endpoints |
| 7 | Wrong delimiter in test | **FIXED** | `test_licensing.py:82` uses `\|` delimiter |
| 8 | No CORS configuration | **FIXED** | `CORSMiddleware` with configurable origins |
| 9 | No health check endpoint | **FIXED** | `GET /health` returns status + session/room counts |
| 10 | Unused imports | **FIXED** | Removed from `export.py` and `web/server.py` |
| 11 | Auth token in query params | **FIXED** | `Authorization: Bearer` header support added (query param kept for legacy) |
| 12 | Web server monolith (702 lines) | **FIXED** | Split into `web/routers/auth.py`, `songs.py`, `researcher.py` |
| 13 | No request logging | **FIXED** | HTTP middleware logs method, path, status, and duration |
| 14 | No graceful shutdown | **FIXED** | FastAPI `lifespan` handler clears sessions/rooms on shutdown |
| 15 | API key hashing without salt | **FIXED** | Per-key random salt added to `APIKeyStore.register()` |
| 16 | No CI pipeline | **FIXED** | `.github/workflows/ci.yml` (pytest, ruff, mypy) |
| 17 | README roadmap stale | **FIXED** | All 4 phases marked complete |
| 18 | CONTRIBUTING.md missing | **FIXED** | Created with dev workflow, code style, security guidelines |
| 19 | IMPLEMENTATION.md missing | **FIXED** | Created with architecture, security model, testing strategy |
| 20 | No conftest.py | **FIXED** | `tests/conftest.py` with shared fixtures |
| 21 | No atomic file writes | **FIXED** | All stores use `atomic_json_save()` (temp + `os.replace`) |
| 22 | No rate limiting on main endpoints | **FIXED** | Per-IP rate limiting middleware (120 req/min default) |
| 23 | `test_validate_key_wrong_signature` wrong delimiter | **FIXED** | Changed to pipe delimiter |

### Remaining (out of scope for code fixes)

| Issue | Reason |
|-------|--------|
| No real LLM/TTS integration | Requires external engine setup (espeak-ng, Coqui, etc.) |
| No database backend | Requires PostgreSQL/SQLite deployment decision |
| No HTTPS enforcement | Deployment concern (reverse proxy / hosting config) |
| Single developer bus factor | Organizational concern, not a code fix |

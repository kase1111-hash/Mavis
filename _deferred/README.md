# Deferred Features

These modules contain data platform features that were set aside during the
refocus to "Mavis the Instrument." They are preserved here for potential
future reintegration.

## Contents

### mavis/researcher_api.py
Anonymized performance data storage, API key management with SHA-256 hashing,
sliding-window rate limiting. Depends on `mavis.storage`.

### mavis/intent_bridge.py
Connects to the intent-engine REST API for prosody-aware analysis. Falls back
to local heuristic analysis. Depends on `mavis.export` and `mavis.llm_processor`.

### mavis/export_bulk.py
Bulk export functions extracted from `mavis/export.py`:
- `export_dataset_jsonl()` -- JSONL export for ML training pipelines
- `generate_audio_for_recording()` -- WAV audio generation
- `validate_iml()` -- IML XML structural validation
- `_write_wav()` -- PCM to WAV writer

### web/routers/researcher.py
FastAPI router for the researcher API endpoints. Depends on `mavis.researcher_api`.

### tests/
Test files for the above modules:
- `test_researcher_api.py`
- `test_intent_bridge.py`
- `test_export_phase4.py`

## Reintegration

To bring these features back:

1. Move `_deferred/mavis/*.py` back to `mavis/`
2. Move `_deferred/web/routers/researcher.py` back to `web/routers/`
3. Move `_deferred/tests/*.py` back to `tests/`
4. Re-add bulk functions to `mavis/export.py` (or import from `export_bulk`)
5. In `web/server.py`, add `from web.routers import researcher` and
   `app.include_router(researcher.router)`
6. Run `python3 -m pytest tests/ -v` to verify

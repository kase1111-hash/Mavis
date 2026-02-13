# Contributing to Mavis

## Getting Started

```bash
# Clone the repo
git clone https://github.com/kase1111-hash/Mavis.git
cd Mavis

# Install in development mode
pip install -e ".[dev]"

# Run the test suite
python3 -m pytest tests/ -v

# Run the interactive demo
python3 demos/interactive_vocal_typing.py
```

## Development Workflow

1. Create a feature branch from `main`.
2. Make changes and add tests for any new functionality.
3. Run the full test suite: `python3 -m pytest tests/ -v`
4. Run the linter: `ruff check mavis/ web/ tests/`
5. Commit with a clear, descriptive message.
6. Open a pull request against `main`.

## Project Structure

- `mavis/` -- Core Python package.
- `web/` -- FastAPI web server with router modules.
- `web/routers/` -- songs and leaderboard router.
- `tests/` -- pytest test suite (170 tests).
- `_deferred/` -- Data platform features set aside for future reintegration.
- `songs/` -- 10-song JSON library.
- `demos/` -- Interactive and non-interactive demos.

## Adding a New Module

1. Create `mavis/your_module.py`.
2. Create `tests/test_your_module.py` with tests.
3. Update `CLAUDE.md` with the module description and any new commands.
4. Run the full test suite to verify no regressions.

## Adding a New Song

1. Create a JSON file in `songs/` following the format of `songs/twinkle.json`.
2. Required fields: `title`, `bpm`, `difficulty` (easy/medium/hard), `sheet_text`, `tokens`.
3. Test with: `python3 -c "from mavis.songs import load_song; print(load_song('songs/yourfile.json'))"`

## Adding a New Sheet Text Markup

See the 6-step process documented in `CLAUDE.md` under "Adding a New Sheet Text Markup".

## Code Style

- Python 3.8+ compatible.
- Line length: 100 characters (configured in `pyproject.toml`).
- Use `@dataclass` for structured data.
- Use `from mavis.storage import atomic_json_save, locked_json_load` for file persistence.
- Every `*Store` class must use atomic writes and file locking.
- No `unittest.mock` -- use domain mock objects (`MockLLMProcessor`, `MockAudioSynthesizer`).

## Security

- All web endpoints go through the rate limiting middleware.

## Test Guidelines

- Every module in `mavis/` must have a corresponding test file in `tests/`.
- Use `tempfile.NamedTemporaryFile` or the `tmp_json_path` fixture from `conftest.py`.
- Include error path and edge case tests.
- Shared helpers go in `tests/conftest.py`.

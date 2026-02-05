# CLAUDE.md - Agent Guide for Mavis

## Project Summary

Mavis is a vocal typing instrument that converts keyboard input with prosody markup ("Sheet Text") into singing via an LLM + TTS pipeline. It is a Python 3.8+ project currently at the proof-of-concept stage with no source code implemented yet -- only documentation (README.md, spec.md, LICENSE).

## Repository Structure

```
/
├── README.md        # Full project description, concept, roadmap
├── spec.md          # Technical specification (architecture, data models, components)
├── LICENSE          # MIT License (Kase Branham, 2026)
└── CLAUDE.md        # This file
```

No source code, tests, configs, or dependency files exist yet.

## Key Concepts

- **Sheet Text**: Prosody markup notation embedded in typed text. CAPS = loud, `_underscores_` = soft, `...` = vibrato, `[brackets]` = harmony, ALL CAPS = shout.
- **Pipeline**: Input Buffer -> LLM Phoneme Processor -> Output Buffer -> Audio Synthesis.
- **Buffer management**: The core gameplay mechanic. Users control vocal output by managing typing speed and pause timing to keep the buffer in an optimal zone.
- **Latency as gameplay**: The 600ms-1.5s processing delay is intentional -- users read ahead in the Sheet Text, absorbing latency through lookahead.

## Tech Stack (Planned)

- **Language**: Python 3.8+
- **LLM**: llama-cpp-python (local) or Anthropic Claude API (cloud)
- **TTS**: espeak-ng (fast/free), Coqui TTS (quality/free), or ElevenLabs (premium)
- **Interface**: Python/PyGame (native), Browser (web), or React Native (mobile)

## Development Guidelines

- There is no build system, package manager config, or test suite yet. When creating these, prefer `pyproject.toml` for Python packaging.
- Demo scripts should go in `demos/`. The README references `demos/vocal_typing_demo.py` and `demos/interactive_vocal_typing.py`.
- The README references `IMPLEMENTATION.md` and `CONTRIBUTING.md` which do not exist yet.
- Follow the data models defined in `spec.md` (Section 7) for Sheet Text tokens, phoneme events, and buffer state.

## Common Tasks

### Starting implementation
1. Create a `mavis/` Python package directory.
2. Set up `pyproject.toml` with Python 3.8+ requirement.
3. Implement the pipeline components in order: input buffer, LLM processor, output buffer, audio synthesis.
4. Create the demo scripts referenced in the README.

### Adding a new Sheet Text markup
1. Add the markup definition to the Sheet Text table in both `README.md` and `spec.md`.
2. Update the input buffer parser to recognize the new token type.
3. Update the LLM phoneme processor to handle the new prosody cue.
4. Add corresponding audio synthesis behavior.

### Running the project
No runnable code exists yet. When demos are created:
```bash
python3 demos/vocal_typing_demo.py
python3 demos/interactive_vocal_typing.py
```

## Architecture Notes

- The input buffer must parse Sheet Text markup into structured tokens before sending to the LLM.
- The LLM outputs timestamped phoneme events with prosody parameters (volume, pitch, vibrato, breathiness).
- The output buffer manages drain rate vs fill rate; its level determines vocal quality (underflow = voice cracks, overflow = pitch strain).
- Hardware capability determines buffer window size and effective difficulty.

## Related Ecosystem

- **prosody-protocol**: Markup language and training dataset.
- **intent-engine**: Prosody-aware AI processing.
- **Agent-OS**: Constitutional AI governance layer.

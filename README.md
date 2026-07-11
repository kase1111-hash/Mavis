# Mavis

**Turn typing into singing. Your keyboard is the instrument you already know how to play.**

![Status](https://img.shields.io/badge/status-proof--of--concept-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

---

## What Is This?

Mavis is a **vocal typing instrument** - a system that transforms your typing behavior into vocal performance using AI-powered phoneme processing.

Unlike traditional instruments (piano, violin) that require years of training in bespoke motor skills, Mavis uses **typing** - a skill you already have from 8+ hours of daily practice. We're just changing the "sound card" attached to the behavior.

**Try typing this:**
```
the SUN... is falling _down_
```

**Mavis sings:**
> "the **SUN** 🎵 is falling *down*"  
> (loud, with vibrato, soft ending)

---

## The Concept

### Traditional Music Education
- ❌ Learn bespoke motor skills (years of practice)
- ❌ No transfer value outside music
- ❌ High barrier to entry
- ❌ Expensive instruments and lessons

### Mavis
- ✅ Use existing typing skills
- ✅ Skills transfer (better typing, better communication)
- ✅ Zero barrier to entry
- ✅ Free and open source

---

## Sheet Text: The Notation System

Instead of reading traditional sheet music, you read "Sheet Text" - formatted text with embedded performance cues:

| Markup | Musical Effect | Example |
|--------|----------------|---------|
| **CAPS** | Loud/chest voice | `the SUN rises` |
| *_underscores_* | Soft/breathy | `falling _gently_` |
| `...` | Vibrato/sustain | `hold... this... note` |
| `[brackets]` | Harmony (Ctrl key) | `singing [together]` |
| `ALL CAPS` | Shouted/distorted | `I SAID STOP` |

### Example Performance

**Sheet Text:**
```
the SUN... is falling _down_
and RISING [again]
```

**How to perform it:**
1. Type `the` normally
2. Slam `SUN` with Shift/Caps (loud)
3. Hold the `N` key for vibrato (`...`)
4. Type `is falling` in italics (soft, breathy)
5. Type `down` with underscore markup
6. Shout `RISING` in all caps
7. Hold Ctrl while typing `again` (triggers harmony)

**What you hear:**
> A voice that starts gentle, builds to an emphatic peak with vibrato, descends breathily, then rises powerfully with harmony.

---

## How It Works

```
┌──────────────┐
│  You Type    │  "the SUN... is falling _down_"
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  Input Buffer                            │
│  [████████░░░░░░] Typing ahead          │
│  (You can type 2-3 seconds in advance)  │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  LLM Phoneme Processing                  │
│  Interprets prosody cues                 │
│  Converts to phoneme stream with timing  │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  Output Buffer                           │
│  [█████░░░░░░░░] Phonemes ready to sing │
│  (Buffer management = breath control)    │
└──────┬───────────────────────────────────┘
       │
       ▼
┌──────────────┐
│  Audio Out   │  🎤 Singing voice
└──────────────┘
```

### The Secret: Latency Becomes Gameplay

Unlike rhythm games (Guitar Hero) where latency = failure, Mavis makes latency **part of the instrument**:

- **Input Buffer:** You can type ahead (like planning your breath)
- **Processing Time:** LLM converts text to phonemes (50-500ms depending on hardware)
- **Output Buffer:** Phonemes wait to be sung (you manage this like breath capacity)

**Total latency:** 600ms - 1.5s (but you're looking 2-3 seconds ahead, so it feels natural)

This means:
- ✅ Works on any hardware (slow computer = bigger buffer = easier mode)
- ✅ Teaches real musical skills (phrasing, breath control, dynamics)
- ✅ Accessible to different input methods (eye-tracking, sip-puff, adaptive keyboards)

---

## Current Status: Alpha (Core Instrument)

This repo contains a **focused alpha implementation** of the core instrument with real grapheme-to-phoneme conversion and speech synthesis via espeak-ng (with mock fallbacks), plus optional Claude API and llama-cpp G2P backends. 204 tests passing.

### What Works
- ✅ Full pipeline (input buffer, sheet text parser, LLM processor, output buffer, audio synthesis)
- ✅ Buffer visualization and interactive typing interface
- ✅ 10-song library with 3 difficulty tiers and 4 difficulty presets
- ✅ Scoring, leaderboards, 6 voice profiles, 7-lesson tutorial
- ✅ Web interface (FastAPI + WebSocket real-time gameplay)
- ✅ Prosody-Protocol IML export (core conversion functions)

### What's Needed for Production
- ✅ Real TTS engine (espeak-ng, pitch-tracked singing voice); Coqui/ElevenLabs still stubs
- ✅ Real G2P (espeak-ng, any English word) with optional Claude API / llama-cpp backends

---

## Quick Start

### Try the Demo

```bash
# Clone the repo
git clone https://github.com/kase1111-hash/Mavis.git
cd Mavis

# Run the pipeline demonstration
python3 demos/vocal_typing_demo.py

# Try interactive typing
python3 demos/interactive_vocal_typing.py
```

### What to Try

In interactive mode, type phrases with prosody markup:

```
the SUN is rising         # CAPS for emphasis
falling _softly_ down     # underscores for breathiness  
hold... this... note...   # ellipses for vibrato
I SAID STOP              # ALL CAPS for shouting
```

Watch the buffers fill and drain. Notice how typing speed affects buffer health.

---

## The Gameplay

Mavis isn't just a synthesizer - it's a **skill-based game** where you learn to:

### Level 1: Data Entry Clerk
- **Goal:** Hit the letters in time
- **Result:** Monotone robotic singing, but on beat

### Level 2: Poet  
- **Goal:** Master holds, emphasis, and dynamics
- **Result:** The voice starts to sound human

### Level 3: Virtuoso
- **Goal:** Use real-time modifiers (Ctrl/Alt for harmonies, Delete for staccato)
- **Result:** Full polyphonic vocal performance

### Buffer Management = Musical Skill

The core mechanic is **managing your breath**:

- **Too empty:** Voice cracks (ran out of breath)
- **Optimal:** Smooth, controlled singing
- **Too full:** Pitch strains (trying to sing too fast)

You control flow by:
- Typing speed (fills buffer)
- Pause timing (drains buffer)
- Planning ahead (maintains optimal level)

---

## Why This Matters

### For Musicians
Learn vocal performance without needing a good singing voice. Express musical ideas instantly.

### For Office Workers
Your daily typing is already rhythmic, already practiced. This just makes it audible.

### For People With Disabilities
- Type with eye-tracking → create vocal performances
- Type with sip-puff → restore singing ability  
- Type with adaptive keyboard → express emotions vocally

The game's difficulty slider becomes an accessibility tool - without stigma, without separate versions.

### For AI Researchers
Every performance generates training data for **prosody ↔ text mapping**, exported as [Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol) IML (Intent Markup Language) documents. This enables:
- Better speech-to-text (that preserves emotional intent)
- Better text-to-speech (that sounds human)
- Better LLMs (that understand how you meant something, not just what you said)

Performance data is exported via `mavis/export.py` in the Prosody-Protocol dataset format (`dataset-entry.schema.json`), with IML markup, emotion labels, and 7-dimensional training feature vectors.

See: [`Prosody-Protocol`](https://github.com/kase1111-hash/Prosody-Protocol)

---

## Technical Architecture

### Hardware Scaling

| Hardware | Model | Latency | Buffer | Difficulty |
|----------|-------|---------|--------|------------|
| Laptop (CPU) | Phi-3 | 800ms | 5s | Easy |
| Desktop (GPU) | Llama 8B | 200ms | 2s | Medium |
| Server (GPU) | Llama 70B | 80ms | 1s | Hard |
| Cloud API | Claude Sonnet | 150ms | 2.5s | Medium |

**Same game, different skill ceiling.** Slower hardware just means more planning required.

### Stack Options

**LLM Processing:**
- Local: llama-cpp-python (sovereignty, zero cost)
- Cloud: Anthropic Claude API (quality, simplicity)

**Audio Synthesis:**
- Fast: espeak-ng (robotic but works)
- Better: Coqui TTS (open source, quality)
- Best: ElevenLabs API (premium, expensive)

**Interface:**
- Web: Browser-based (widest reach)
- Native: Python/PyGame (lowest latency)

See [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) for complete technical specs.

---

## Roadmap

### Phase 1: Playable Alpha -- COMPLETE
- [x] LLM integration (espeak-ng G2P, Claude API, llama-cpp, mock)
- [x] TTS integration (mock sine-wave synthesis + stubs)
- [x] Visual sustain bars
- [x] 10 playable songs across 3 difficulty tiers
- [x] Scoring and grading system

### Phase 2: Game Polish -- COMPLETE
- [x] Song library (10 songs)
- [x] 4 difficulty levels (Easy/Medium/Hard/Expert)
- [x] Local JSON leaderboards
- [x] 6 voice customization presets
- [x] 7-lesson tutorial mode

### Phase 3: Web Interface -- COMPLETE
- [x] Web version (FastAPI + WebSocket)

### Phase 4: Make It Sing -- IN PROGRESS
- [x] Real TTS integration (espeak-ng) -- pitch-tracked singing voice, auto-detected when installed
- [x] Real LLM integration (Claude API + llama-cpp-python, with espeak-ng G2P as the offline default)
- [x] Export to Prosody-Protocol IML (core conversion functions)

---

## Philosophy

**This isn't "making typing musical."**

**This is revealing that typing already was musical** - we just never had the right "sound card" to hear it.

When you type `the SUN is falling DOWN`, you already hear the emphasis. You already know where the stress goes. You already have the prosody in your head.

Mavis just **makes that audible**.

---

## Contributing

We're in proof-of-concept stage. Contributions welcome in:

- **Code:** LLM integration, TTS engines, UI/UX
- **Music:** Song creation, notation design
- **Research:** Prosody detection, accessibility studies
- **Documentation:** Tutorials, guides, translations

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for guidelines.

---

## Related Projects

Part of the **Natural Language Ecosystem:**

- **[Prosody-Protocol](https://github.com/kase1111-hash/Prosody-Protocol)** - IML specification, JSON schemas, Python SDK, and training infrastructure. Mavis exports performance data to this format.
- **intent-engine** - Prosody-aware AI system (consumes IML from Prosody-Protocol)
- **Agent-OS** - Constitutional AI governance (uses intent-engine)

---

## License

MIT License - See [LICENSE](./LICENSE)

Built with constitutional AI principles. Your data stays yours. No surveillance, no exploitation.

---

## Contact

**Creator:** Kase ([True North Construction LLC](https://truenorthconstruction.example))  
**Email:** kase@truenorthconstruction.example  
**Philosophy:** Sovereignty, local control, owned infrastructure

Part of the natural language programming movement.

---

## Acknowledgments

Inspired by:
- **Mavis Beacon Teaches Typing** (the original keyboard skill trainer)
- **Guitar Hero** (rhythm game mechanics)
- **Constitutional AI** (Anthropic's framework for aligned systems)
- Every office worker who's spent 20 years practicing the "instrument" without knowing it

---

**Question:** What does it sound like when a nation of office workers discovers they're already musicians?

**Answer:** We're about to find out.

🎤 **Type. Sing. Repeat.**

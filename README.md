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

## Current Status: Proof of Concept

This repo currently contains **demonstration code** that simulates the full pipeline.

### What Works
- ✅ Input buffering simulation
- ✅ Buffer visualization
- ✅ Simulated LLM prosody processing
- ✅ Latency modeling across different hardware
- ✅ Interactive typing interface

### What's Needed for MVP
- ⏳ Real LLM integration (Llama, Claude API)
- ⏳ Real TTS engine (espeak-ng, Coqui, ElevenLabs)
- ⏳ Visual sustain bars (like Guitar Hero)
- ⏳ First playable song
- ⏳ Scoring system
- ⏳ Audio synthesis pipeline

**Estimated time to playable alpha:** 6 weeks part-time

---

## Quick Start

### Try the Demo

```bash
# Clone the repo
git clone https://github.com/yourusername/mavis.git
cd mavis

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
Every performance generates training data for **prosody ↔ text mapping**, which enables:
- Better speech-to-text (that preserves emotional intent)
- Better text-to-speech (that sounds human)
- Better LLMs (that understand how you meant something, not just what you said)

See: [`prosody-protocol`](https://github.com/yourusername/prosody-protocol) and [`intent-engine`](https://github.com/yourusername/intent-engine)

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
- Mobile: React Native (accessibility)

See [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) for complete technical specs.

---

## Roadmap

### Phase 1: Playable Alpha (6 weeks)
- [ ] LLM integration (local Llama)
- [ ] TTS integration (espeak-ng)
- [ ] Visual sustain bars
- [ ] One playable song
- [ ] Basic scoring

### Phase 2: Game Polish (4 weeks)
- [ ] Song library (10 songs)
- [ ] Multiple difficulty levels
- [ ] Leaderboards
- [ ] Voice customization
- [ ] Tutorial mode

### Phase 3: Platform Launch (8 weeks)
- [ ] Web version
- [ ] Mobile apps (iOS/Android)
- [ ] Cloud save
- [ ] Multiplayer/duets
- [ ] User-generated content

### Phase 4: Ecosystem Integration
- [ ] Export to prosody-protocol dataset
- [ ] Integration with intent-engine
- [ ] API for researchers
- [ ] Institutional licensing (therapy, education)

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

- **[prosody-protocol](https://github.com/yourusername/prosody-protocol)** - The markup language and training dataset
- **[intent-engine](https://github.com/yourusername/intent-engine)** - Prosody-aware AI system
- **[Agent-OS](https://github.com/yourusername/agent-os)** - Constitutional AI governance (uses intent-engine)

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

# Mavis - Technical Specification

## 1. Overview

Mavis is a vocal typing instrument that transforms keyboard typing into vocal performance using AI-powered phoneme processing. The user types text with embedded prosody markup ("Sheet Text"), which is processed through an LLM and synthesized into singing audio in real time.

**Project stage:** Proof of concept
**Language:** Python 3.8+
**License:** MIT

---

## 2. Core Concept

Users type formatted text containing prosody cues. A pipeline converts this input into phoneme streams, which are synthesized into vocal audio output. Latency between typing and audio output is treated as a game mechanic (buffer management), not a defect.

---

## 3. Sheet Text Notation

Sheet Text is the markup language used to encode performance instructions within typed text.

| Markup | Effect | Input Example | Behavior |
|--------|--------|---------------|----------|
| CAPS (Shift held) | Loud / chest voice | `the SUN rises` | Increase volume and formant intensity |
| `_underscores_` | Soft / breathy | `falling _gently_` | Reduce volume, add breathiness |
| `...` (ellipsis) | Vibrato / sustain | `hold... this...` | Extend phoneme duration, add pitch modulation |
| `[brackets]` | Harmony (Ctrl key) | `singing [together]` | Layer additional harmonic voice |
| ALL CAPS | Shouted / distorted | `I SAID STOP` | Maximum volume, distortion effect |

---

## 4. System Architecture

### 4.1 Pipeline

```
Keyboard Input -> Input Buffer -> LLM Phoneme Processor -> Output Buffer -> Audio Synthesis -> Speaker
```

### 4.2 Components

#### 4.2.1 Input Buffer
- Captures raw keystrokes and typed text.
- Supports type-ahead: the user can type 2-3 seconds ahead of the audio output.
- Parses Sheet Text markup into structured tokens (plain text, emphasis markers, sustain markers, harmony triggers).

#### 4.2.2 LLM Phoneme Processor
- Accepts structured tokens from the input buffer.
- Interprets prosody cues (volume, pitch, duration, breathiness, vibrato).
- Converts text into a timestamped phoneme stream with associated prosody parameters.
- Must operate within the latency budget (50-500ms depending on hardware).

**LLM options:**
| Provider | Model | Expected Latency |
|----------|-------|-------------------|
| Local (CPU) | Phi-3 | ~800ms |
| Local (GPU) | Llama 8B | ~200ms |
| Local (GPU, large) | Llama 70B | ~80ms |
| Cloud | Anthropic Claude | ~150ms |

#### 4.2.3 Output Buffer
- Stores processed phoneme stream awaiting synthesis.
- Buffer level is the core game mechanic ("breath control").
- States:
  - **Too empty:** Voice cracks / audio dropout (ran out of "breath").
  - **Optimal:** Smooth, controlled vocal output.
  - **Too full:** Pitch strain / rushed delivery (buffer overflow pressure).

#### 4.2.4 Audio Synthesis (TTS)
- Converts phoneme stream with prosody parameters into audio waveform.
- Plays audio to speaker in real time.

**TTS options:**
| Engine | Quality | Latency | Cost |
|--------|---------|---------|------|
| espeak-ng | Low (robotic) | Very low | Free |
| Coqui TTS | Medium-high | Medium | Free (open source) |
| ElevenLabs API | High | Medium | Paid |

### 4.3 Latency Model

Total end-to-end latency: **600ms - 1.5s** (varies by hardware).

The user reads Sheet Text 2-3 seconds ahead of the current audio position, so the latency is absorbed by lookahead rather than perceived as delay.

| Hardware | Total Latency | Buffer Window | Effective Difficulty |
|----------|--------------|---------------|---------------------|
| Laptop (CPU) | ~800ms | 5s | Easy (more planning time) |
| Desktop (GPU) | ~200ms | 2s | Medium |
| Server (GPU) | ~80ms | 1s | Hard (less margin) |
| Cloud API | ~150ms | 2.5s | Medium |

---

## 5. Gameplay Mechanics

### 5.1 Skill Progression

| Level | Name | Skills | Audio Result |
|-------|------|--------|-------------|
| 1 | Data Entry Clerk | Hit letters on time | Monotone robotic singing, on beat |
| 2 | Poet | Holds, emphasis, dynamics | Human-sounding voice |
| 3 | Virtuoso | Real-time modifiers (Ctrl/Alt for harmonies, Delete for staccato) | Full polyphonic vocal performance |

### 5.2 Buffer Management

The player's primary skill is maintaining optimal buffer levels:

- **Typing speed** fills the buffer.
- **Pause timing** drains the buffer.
- **Planning ahead** keeps the buffer in the optimal zone.

### 5.3 Modifier Keys

| Key | Effect |
|-----|--------|
| Shift / Caps Lock | Loud / emphasis |
| Ctrl (held) | Harmony layer |
| Alt (held) | Reserved for future modifiers |
| Delete | Staccato (cut note short) |

---

## 6. Interface Options

| Platform | Technology | Tradeoff |
|----------|-----------|----------|
| Web | Browser-based | Widest reach, higher audio latency |
| Native | Python / PyGame | Lowest latency, requires install |
| Mobile | React Native | Accessibility, touch input |

---

## 7. Data Model

### 7.1 Sheet Text Token

```
{
  "text": string,          // Raw text content
  "emphasis": enum,        // none | soft | loud | shout
  "sustain": boolean,      // Whether to apply vibrato/sustain
  "harmony": boolean,      // Whether to layer harmony
  "duration_modifier": float  // Multiplier on default phoneme duration
}
```

### 7.2 Phoneme Event

```
{
  "phoneme": string,       // IPA phoneme symbol
  "start_ms": int,         // Start time in milliseconds
  "duration_ms": int,      // Duration in milliseconds
  "volume": float,         // 0.0 - 1.0
  "pitch_hz": float,       // Fundamental frequency
  "vibrato": boolean,      // Pitch modulation flag
  "breathiness": float,    // 0.0 - 1.0
  "harmony_intervals": [int]  // Semitone offsets for harmony voices
}
```

### 7.3 Buffer State

```
{
  "level": float,          // 0.0 (empty) - 1.0 (full)
  "status": enum,          // underflow | optimal | overflow
  "drain_rate": float,     // Phonemes consumed per second
  "fill_rate": float       // Tokens received per second
}
```

---

## 8. Accessibility

The system is designed for multiple input methods:

- Standard keyboard
- Eye-tracking systems
- Sip-puff controllers
- Adaptive keyboards
- Any device that can produce character input

Difficulty scaling (via buffer window size) doubles as an accessibility control -- slower processing means more forgiving timing without requiring a separate "accessible" mode.

---

## 9. Planned Demo Files

| File | Purpose |
|------|---------|
| `demos/vocal_typing_demo.py` | Non-interactive pipeline demonstration showing buffer flow |
| `demos/interactive_vocal_typing.py` | Interactive mode where user types Sheet Text and sees buffer visualization |

---

## 10. Roadmap

### Phase 1 - Playable Alpha
- LLM integration (local Llama via llama-cpp-python)
- TTS integration (espeak-ng)
- Visual sustain bars
- One playable song
- Basic scoring system

### Phase 2 - Game Polish
- Song library (10 songs)
- Multiple difficulty levels
- Leaderboards
- Voice customization
- Tutorial mode

### Phase 3 - Platform Launch
- Web version
- Mobile apps (iOS / Android)
- Cloud save
- Multiplayer / duets
- User-generated content

### Phase 4 - Ecosystem Integration
- Export to prosody-protocol dataset format
- Integration with intent-engine
- Researcher API
- Institutional licensing (therapy, education)

---

## 11. Related Projects

| Project | Role |
|---------|------|
| prosody-protocol | Markup language and training dataset for prosody |
| intent-engine | Prosody-aware AI system |
| Agent-OS | Constitutional AI governance layer (uses intent-engine) |

---

## 12. Open Questions

- Final choice of local LLM model for Phase 1.
- Phoneme set: full IPA vs. simplified subset for MVP.
- Scoring algorithm: accuracy-weighted vs. expressiveness-weighted.
- Audio synthesis: single voice or voice selection from Phase 1.
- Web audio latency: acceptable threshold for browser-based version.

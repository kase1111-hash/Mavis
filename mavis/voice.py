"""Voice customization -- configurable voice profiles with persistence."""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
class VoiceProfile:
    """A customizable voice profile that modifies synthesis parameters.

    Attributes:
        name: Display name for the voice.
        base_pitch_hz: Base fundamental frequency (higher = higher voice).
        pitch_range: Pitch variation range multiplier (1.0 = normal).
        vibrato_depth: Vibrato depth in Hz (0 = no vibrato).
        vibrato_rate: Vibrato rate in Hz.
        breathiness: Default breathiness level (0.0-1.0).
        volume_scale: Overall volume multiplier.
        timbre: Timbre label (used by future TTS backends).
        description: Short description for UI display.
    """

    name: str
    base_pitch_hz: float = 220.0
    pitch_range: float = 1.0
    vibrato_depth: float = 10.0
    vibrato_rate: float = 5.0
    breathiness: float = 0.0
    volume_scale: float = 1.0
    timbre: str = "neutral"
    description: str = ""


# Predefined voice presets
VOICES: Dict[str, VoiceProfile] = {
    "default": VoiceProfile(
        name="Default",
        base_pitch_hz=220.0,
        description="Standard neutral voice.",
    ),
    "alto": VoiceProfile(
        name="Alto",
        base_pitch_hz=196.0,
        pitch_range=0.9,
        vibrato_depth=8.0,
        timbre="warm",
        description="Warm lower register.",
    ),
    "soprano": VoiceProfile(
        name="Soprano",
        base_pitch_hz=330.0,
        pitch_range=1.2,
        vibrato_depth=12.0,
        timbre="bright",
        description="Bright higher register.",
    ),
    "bass": VoiceProfile(
        name="Bass",
        base_pitch_hz=110.0,
        pitch_range=0.8,
        vibrato_depth=6.0,
        volume_scale=1.1,
        timbre="deep",
        description="Deep lower register.",
    ),
    "whisper": VoiceProfile(
        name="Whisper",
        base_pitch_hz=200.0,
        pitch_range=0.5,
        vibrato_depth=0.0,
        breathiness=0.7,
        volume_scale=0.5,
        timbre="breathy",
        description="Soft, breathy whisper voice.",
    ),
    "robot": VoiceProfile(
        name="Robot",
        base_pitch_hz=180.0,
        pitch_range=0.3,
        vibrato_depth=0.0,
        vibrato_rate=0.0,
        breathiness=0.0,
        volume_scale=0.9,
        timbre="metallic",
        description="Flat, mechanical tone.",
    ),
}


def get_voice(name: str) -> VoiceProfile:
    """Look up a voice preset by name (case-insensitive).

    Raises:
        KeyError: If the voice name is not recognized.
    """
    key = name.lower()
    if key not in VOICES:
        valid = ", ".join(sorted(VOICES))
        raise KeyError(f"Unknown voice {name!r}. Valid: {valid}")
    return VOICES[key]


def list_voices() -> List[VoiceProfile]:
    """Return all voice presets sorted by base pitch."""
    return sorted(VOICES.values(), key=lambda v: v.base_pitch_hz)


def save_voice_preference(voice_name: str, path: Optional[str] = None) -> None:
    """Persist the user's preferred voice to a JSON file.

    Default path: ``~/.mavis/voice.json``
    """
    if path is None:
        path = os.path.join(os.path.expanduser("~"), ".mavis", "voice.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    data = {"selected_voice": voice_name}
    # Also save any custom voice if it's not a preset
    voice = VOICES.get(voice_name.lower())
    if voice is not None:
        data["profile"] = asdict(voice)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_voice_preference(path: Optional[str] = None) -> str:
    """Load the user's preferred voice name from the JSON file.

    Returns "default" if no preference file exists.
    """
    if path is None:
        path = os.path.join(os.path.expanduser("~"), ".mavis", "voice.json")
    if not os.path.isfile(path):
        return "default"
    with open(path, "r") as f:
        data = json.load(f)
    return data.get("selected_voice", "default")

"""Central configuration for hardware profiles, buffer sizes, and backend selection."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HardwareProfile:
    """Hardware capability profile that determines latency and difficulty."""

    name: str
    total_latency_ms: int
    buffer_window_s: float
    difficulty: str  # "easy" | "medium" | "hard"


# Predefined profiles (from spec.md Section 4.3)
LAPTOP_CPU = HardwareProfile("Laptop (CPU)", 800, 5.0, "easy")
DESKTOP_GPU = HardwareProfile("Desktop (GPU)", 200, 2.0, "medium")
SERVER_GPU = HardwareProfile("Server (GPU)", 80, 1.0, "hard")
CLOUD_API = HardwareProfile("Cloud API", 150, 2.5, "medium")


@dataclass
class MavisConfig:
    """Top-level configuration for a Mavis pipeline instance."""

    hardware: HardwareProfile = field(default_factory=lambda: LAPTOP_CPU)
    input_buffer_capacity: int = 256
    output_buffer_capacity: int = 32
    llm_backend: str = "mock"  # "mock" | "llama" | "claude"
    tts_backend: str = "mock"  # "mock" | "espeak" | "coqui" | "elevenlabs"
    difficulty_name: Optional[str] = None  # if set, overrides buffer sizes from difficulty
    voice_name: Optional[str] = None  # if set, applies voice profile to synthesis
    # Phonemes sung (drained from the output buffer) per second of real time,
    # before the difficulty's drain_rate_multiplier is applied. Calibrated so a
    # typist producing ~0.7 phonemes per character can outpace the drain at
    # normal typing speed but falls behind when they stop.
    base_drain_rate: float = 3.0

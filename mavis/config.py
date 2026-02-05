"""Central configuration for hardware profiles, buffer sizes, and backend selection."""

from dataclasses import dataclass, field


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
    output_buffer_capacity: int = 128
    llm_backend: str = "mock"  # "mock" | "llama" | "claude"
    tts_backend: str = "mock"  # "mock" | "espeak" | "coqui" | "elevenlabs"

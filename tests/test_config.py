"""Tests for mavis.config."""

from mavis.config import (
    CLOUD_API,
    DESKTOP_GPU,
    LAPTOP_CPU,
    SERVER_GPU,
    HardwareProfile,
    MavisConfig,
)


def test_hardware_profiles_exist():
    assert LAPTOP_CPU.name == "Laptop (CPU)"
    assert DESKTOP_GPU.difficulty == "medium"
    assert SERVER_GPU.difficulty == "hard"
    assert CLOUD_API.total_latency_ms == 150


def test_default_config():
    cfg = MavisConfig()
    assert cfg.hardware == LAPTOP_CPU
    assert cfg.llm_backend == "mock"
    assert cfg.tts_backend == "mock"
    assert cfg.input_buffer_capacity == 256
    assert cfg.output_buffer_capacity == 128


def test_custom_config():
    cfg = MavisConfig(
        hardware=SERVER_GPU,
        llm_backend="llama",
        tts_backend="espeak",
    )
    assert cfg.hardware.difficulty == "hard"
    assert cfg.llm_backend == "llama"

"""Tests for mavis.voice."""

import json
import os
import tempfile

import pytest

from mavis.voice import (
    VOICES,
    VoiceProfile,
    get_voice,
    list_voices,
    load_voice_preference,
    save_voice_preference,
)


def test_preset_count():
    assert len(VOICES) >= 6  # default, alto, soprano, bass, whisper, robot


def test_default_voice():
    v = get_voice("default")
    assert v.name == "Default"
    assert v.base_pitch_hz == 220.0


def test_get_voice_case_insensitive():
    v1 = get_voice("Soprano")
    v2 = get_voice("soprano")
    v3 = get_voice("SOPRANO")
    assert v1.name == v2.name == v3.name


def test_get_voice_unknown():
    with pytest.raises(KeyError):
        get_voice("nonexistent")


def test_list_voices_sorted_by_pitch():
    voices = list_voices()
    pitches = [v.base_pitch_hz for v in voices]
    assert pitches == sorted(pitches)


def test_soprano_higher_than_bass():
    soprano = get_voice("soprano")
    bass = get_voice("bass")
    assert soprano.base_pitch_hz > bass.base_pitch_hz


def test_whisper_has_breathiness():
    whisper = get_voice("whisper")
    assert whisper.breathiness > 0.0
    assert whisper.volume_scale < 1.0


def test_robot_no_vibrato():
    robot = get_voice("robot")
    assert robot.vibrato_depth == 0.0


def test_save_and_load_preference():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "voice.json")
        save_voice_preference("soprano", path)

        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert data["selected_voice"] == "soprano"

        loaded = load_voice_preference(path)
        assert loaded == "soprano"


def test_load_preference_default_when_missing():
    result = load_voice_preference("/nonexistent/path/voice.json")
    assert result == "default"


def test_voice_profile_fields():
    v = VoiceProfile(name="Test", base_pitch_hz=440.0, description="test voice")
    assert v.name == "Test"
    assert v.base_pitch_hz == 440.0
    assert v.pitch_range == 1.0  # default
    assert v.volume_scale == 1.0  # default

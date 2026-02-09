"""Tests for mavis.intent_bridge -- prosody-aware analysis of performances."""

from mavis.intent_bridge import IntentBridge, _compute_energy_curve, _generate_coaching
from mavis.export import PerformanceRecording, extract_training_features
from mavis.llm_processor import PhonemeEvent


def _make_event(volume=0.5, pitch_hz=220.0, duration_ms=100, vibrato=False, breathiness=0.0):
    return PhonemeEvent(
        phoneme="AH", start_ms=0, duration_ms=duration_ms,
        volume=volume, pitch_hz=pitch_hz, vibrato=vibrato,
        breathiness=breathiness, harmony_intervals=[],
    )


def test_bridge_init():
    bridge = IntentBridge()
    assert bridge.service_url == "http://localhost:8100"
    assert bridge.timeout_s == 5.0


def test_bridge_is_available_offline():
    bridge = IntentBridge(service_url="http://localhost:99999")
    assert not bridge.is_available()


def test_local_analyze_empty():
    bridge = IntentBridge()
    bridge._available = False
    result = bridge.analyze({"phoneme_events": []})
    assert result["dominant_emotion"] == "neutral"
    assert result["energy_curve"] == []
    assert result["intent_confidence"] == 0.0


def test_local_analyze_basic():
    bridge = IntentBridge()
    bridge._available = False
    events = [_make_event(volume=0.5, pitch_hz=220.0) for _ in range(10)]
    result = bridge.analyze({"phoneme_events": events})
    assert "dominant_emotion" in result
    assert "energy_curve" in result
    assert len(result["energy_curve"]) == 10
    assert "intent_confidence" in result
    assert "coaching_suggestions" in result


def test_local_analyze_loud():
    bridge = IntentBridge()
    bridge._available = False
    events = [_make_event(volume=0.9, pitch_hz=300.0) for _ in range(10)]
    result = bridge.analyze({"phoneme_events": events})
    assert result["dominant_emotion"] == "angry"


def test_local_analyze_triumphant():
    bridge = IntentBridge()
    bridge._available = False
    # Start quiet, end loud
    events = [_make_event(volume=0.2) for _ in range(5)]
    events += [_make_event(volume=0.9) for _ in range(5)]
    result = bridge.analyze({"phoneme_events": events})
    assert result["dominant_emotion"] == "triumphant"


def test_local_analyze_dict_events():
    bridge = IntentBridge()
    bridge._available = False
    events = [
        {"phoneme": "AH", "volume": 0.5, "pitch_hz": 220.0, "duration_ms": 100},
        {"phoneme": "EH", "volume": 0.6, "pitch_hz": 230.0, "duration_ms": 100},
    ]
    result = bridge.analyze({"phoneme_events": events})
    assert "dominant_emotion" in result


def test_analyze_recording():
    bridge = IntentBridge()
    bridge._available = False
    rec = PerformanceRecording(transcript="hello world")
    rec.phoneme_events = [_make_event() for _ in range(5)]
    result = bridge.analyze_recording(rec)
    assert "dominant_emotion" in result


def test_get_feedback():
    bridge = IntentBridge()
    analysis = {
        "dominant_emotion": "joyful",
        "energy_curve": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.7, 0.6, 0.5, 0.4],
        "intent_confidence": 0.7,
    }
    feedback = bridge.get_feedback(analysis)
    assert "bright" in feedback or "uplifting" in feedback


def test_get_feedback_low_confidence():
    bridge = IntentBridge()
    analysis = {
        "dominant_emotion": "neutral",
        "energy_curve": [0.5] * 10,
        "intent_confidence": 0.3,
    }
    feedback = bridge.get_feedback(analysis)
    assert "Low confidence" in feedback


def test_get_coaching():
    bridge = IntentBridge()
    analysis = {"coaching_suggestions": ["Try more contrast.", "Use sustain."]}
    suggestions = bridge.get_coaching(analysis)
    assert len(suggestions) == 2


def test_compute_energy_curve():
    events = [_make_event(volume=0.3) for _ in range(5)]
    events += [_make_event(volume=0.8) for _ in range(5)]
    curve = _compute_energy_curve(events, segments=2)
    assert len(curve) == 2
    assert curve[0] < curve[1]


def test_compute_energy_curve_empty():
    curve = _compute_energy_curve([], segments=5)
    assert curve == []


def test_generate_coaching_flat():
    features = [220.0, 0.0, 0.5, 0.05, 0.01, 5.0, 0.05]
    curve = [0.5] * 10
    suggestions = _generate_coaching(features, curve)
    assert any("contrast" in s.lower() or "dynamic" in s.lower() for s in suggestions)


def test_generate_coaching_no_vibrato():
    features = [220.0, 50.0, 0.5, 0.3, 0.01, 5.0, 0.0]
    suggestions = _generate_coaching(features, [0.5] * 10)
    assert any("sustain" in s.lower() or "vibrato" in s.lower() for s in suggestions)


def test_generate_coaching_too_loud():
    features = [220.0, 50.0, 0.85, 0.3, 0.1, 5.0, 0.2]
    suggestions = _generate_coaching(features, [0.8] * 10)
    assert any("loud" in s.lower() or "quiet" in s.lower() for s in suggestions)

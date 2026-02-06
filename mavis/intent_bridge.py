"""Intent-engine integration -- prosody-aware AI analysis of performances.

Provides IntentBridge for connecting to the intent-engine service. When
the service is unavailable, analysis degrades gracefully to local heuristics.

The intent-engine project consumes IML documents and returns prosody intent
analysis, including emotion classification, energy curves, and coaching
suggestions.
"""

from typing import Any, Dict, List, Optional

from mavis.export import (
    PerformanceRecording,
    extract_training_features,
    infer_emotion,
    phoneme_events_to_iml,
)
from mavis.llm_processor import PhonemeEvent


class IntentBridge:
    """Bridge to the intent-engine service for prosody analysis.

    When the intent-engine is reachable, sends IML documents over HTTP
    for AI-powered analysis. When unavailable, falls back to local
    heuristic analysis using the export module's feature extraction.

    Args:
        service_url: Base URL of the intent-engine REST API.
        timeout_s: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        service_url: str = "http://localhost:8100",
        timeout_s: float = 5.0,
    ):
        self.service_url = service_url.rstrip("/")
        self.timeout_s = timeout_s
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if the intent-engine service is reachable."""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.service_url}/health",
                method="GET",
            )
            urllib.request.urlopen(req, timeout=self.timeout_s)
            self._available = True
            return True
        except Exception:
            self._available = False
            return False

    def analyze(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a performance recording through the intent-engine.

        Sends the IML document to the intent-engine REST API. Falls back
        to local heuristic analysis if the service is unavailable.

        Args:
            performance_data: Dict with keys 'phoneme_events' (list of
                PhonemeEvent-like dicts) and optionally 'transcript'.

        Returns:
            Dict with keys: dominant_emotion, energy_curve, intent_confidence,
            feedback, coaching_suggestions.
        """
        phoneme_events = performance_data.get("phoneme_events", [])
        transcript = performance_data.get("transcript", "")

        # Convert dict-form phoneme events to PhonemeEvent objects if needed
        events = _ensure_phoneme_events(phoneme_events)

        # Try remote analysis first
        if self._available is not False:
            try:
                return self._remote_analyze(events, transcript)
            except Exception:
                self._available = False

        # Fall back to local analysis
        return self._local_analyze(events, transcript)

    def analyze_recording(self, recording: PerformanceRecording) -> Dict[str, Any]:
        """Analyze a PerformanceRecording directly."""
        return self.analyze({
            "phoneme_events": recording.phoneme_events,
            "transcript": recording.transcript,
        })

    def get_feedback(self, analysis: Dict[str, Any]) -> str:
        """Generate human-readable feedback text from an analysis result."""
        emotion = analysis.get("dominant_emotion", "neutral")
        confidence = analysis.get("intent_confidence", 0.0)
        energy = analysis.get("energy_curve", [])

        parts = []

        # Emotion feedback
        emotion_descriptions = {
            "neutral": "Your performance had a balanced, even tone.",
            "angry": "Your performance conveyed intensity and power.",
            "joyful": "Your performance was bright and uplifting.",
            "sad": "Your performance had a soft, melancholic quality.",
            "calm": "Your performance was gentle and controlled.",
            "triumphant": "Your performance conveyed increasing energy and a triumphant climax.",
        }
        parts.append(emotion_descriptions.get(emotion, f"Detected emotion: {emotion}."))

        # Energy feedback
        if len(energy) >= 3:
            start_energy = sum(energy[:len(energy) // 3]) / max(1, len(energy) // 3)
            end_energy = sum(energy[-len(energy) // 3:]) / max(1, len(energy) // 3)
            if end_energy > start_energy + 0.2:
                parts.append("Energy built nicely toward the end.")
            elif start_energy > end_energy + 0.2:
                parts.append("Energy tapered off toward the end.")
            else:
                parts.append("Energy was consistent throughout.")

        # Confidence qualifier
        if confidence < 0.5:
            parts.append("(Low confidence in this analysis.)")

        return " ".join(parts)

    def get_coaching(self, analysis: Dict[str, Any]) -> List[str]:
        """Extract coaching suggestions from analysis results."""
        return analysis.get("coaching_suggestions", [])

    def _remote_analyze(
        self, events: List[PhonemeEvent], transcript: str
    ) -> Dict[str, Any]:
        """Send analysis request to the intent-engine service."""
        import json
        import urllib.request

        iml = phoneme_events_to_iml(events, transcript=transcript)
        features = extract_training_features(events)

        payload = json.dumps({
            "iml": iml,
            "features": features,
            "transcript": transcript,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.service_url}/api/analyze",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=self.timeout_s)
        return json.loads(resp.read().decode("utf-8"))

    def _local_analyze(
        self, events: List[PhonemeEvent], transcript: str
    ) -> Dict[str, Any]:
        """Perform local heuristic analysis when intent-engine is unavailable."""
        if not events:
            return {
                "dominant_emotion": "neutral",
                "energy_curve": [],
                "intent_confidence": 0.0,
                "feedback": "No performance data to analyze.",
                "coaching_suggestions": [],
            }

        features = extract_training_features(events)
        emotion = infer_emotion(events)

        # Compute energy curve (volume over time, in 10 segments)
        energy_curve = _compute_energy_curve(events, segments=10)

        # Compute intent confidence from feature variance
        mean_vol = features[2]  # mean_volume
        vol_range = features[3]  # volume_range
        confidence = min(1.0, 0.3 + vol_range + abs(mean_vol - 0.5))

        # Check for triumphant pattern (rising energy ending loud)
        if len(energy_curve) >= 3:
            if energy_curve[-1] > 0.7 and energy_curve[-1] > energy_curve[0] + 0.2:
                emotion = "triumphant"

        # Generate coaching suggestions
        suggestions = _generate_coaching(features, energy_curve)

        return {
            "dominant_emotion": emotion,
            "energy_curve": energy_curve,
            "intent_confidence": round(confidence, 2),
            "feedback": "",  # Populated by get_feedback()
            "coaching_suggestions": suggestions,
        }


def _ensure_phoneme_events(events: Any) -> List[PhonemeEvent]:
    """Convert dict-form events to PhonemeEvent objects if needed."""
    if not events:
        return []
    if isinstance(events[0], PhonemeEvent):
        return events
    result = []
    for e in events:
        if isinstance(e, dict):
            result.append(PhonemeEvent(
                phoneme=e.get("phoneme", "?"),
                start_ms=e.get("start_ms", 0),
                duration_ms=e.get("duration_ms", 100),
                volume=e.get("volume", 0.5),
                pitch_hz=e.get("pitch_hz", 220.0),
                vibrato=e.get("vibrato", False),
                breathiness=e.get("breathiness", 0.0),
                harmony_intervals=e.get("harmony_intervals", []),
            ))
        else:
            result.append(e)
    return result


def _compute_energy_curve(
    events: List[PhonemeEvent], segments: int = 10
) -> List[float]:
    """Compute energy (volume) over time, returning a list of segment averages."""
    if not events:
        return []
    total_dur = sum(e.duration_ms for e in events)
    if total_dur <= 0:
        return [0.0] * segments

    seg_dur = total_dur / segments
    curve = []
    seg_vols: List[float] = []
    seg_end = seg_dur
    elapsed = 0.0

    for event in events:
        elapsed += event.duration_ms
        seg_vols.append(event.volume)
        if elapsed >= seg_end:
            avg = sum(seg_vols) / len(seg_vols) if seg_vols else 0.0
            curve.append(round(avg, 2))
            seg_vols = []
            seg_end += seg_dur

    # Flush remaining
    if seg_vols:
        curve.append(round(sum(seg_vols) / len(seg_vols), 2))

    # Pad or trim to exact segment count
    while len(curve) < segments:
        curve.append(curve[-1] if curve else 0.0)
    return curve[:segments]


def _generate_coaching(
    features: List[float], energy_curve: List[float]
) -> List[str]:
    """Generate coaching suggestions from feature analysis."""
    suggestions = []
    mean_vol = features[2]
    vol_range = features[3]
    mean_breath = features[4]
    vibrato_ratio = features[6]

    if vol_range < 0.15:
        suggestions.append(
            "Try more dynamic contrast -- vary between soft and loud passages."
        )
    if mean_breath < 0.05:
        suggestions.append(
            "Experiment with breathy soft passages using _underscore_ markup."
        )
    if vibrato_ratio < 0.1:
        suggestions.append(
            "Add sustain (...) to held notes for more expressive vibrato."
        )
    if len(energy_curve) >= 3:
        mid = len(energy_curve) // 2
        if all(abs(energy_curve[i] - energy_curve[0]) < 0.1 for i in range(len(energy_curve))):
            suggestions.append(
                "Your energy was very flat. Try building intensity through the piece."
            )
    if mean_vol > 0.8:
        suggestions.append(
            "You're playing very loud overall. Quieter sections create more impact."
        )
    if mean_vol < 0.3:
        suggestions.append(
            "Your performance is quite soft. Try adding some loud (CAPS) emphasis."
        )

    return suggestions

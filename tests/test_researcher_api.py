"""Tests for mavis.researcher_api -- performance store, API keys, rate limiting."""

import os
import tempfile

from mavis.researcher_api import AnonymizedPerformance, APIKeyStore, PerformanceStore


def _make_perf(perf_id="p1", song_id="twinkle", difficulty="easy", score=100):
    return AnonymizedPerformance(
        perf_id=perf_id,
        song_id=song_id,
        difficulty=difficulty,
        score=score,
        grade="B",
        token_count=10,
        phoneme_count=20,
        emotion="neutral",
        features=[220.0, 50.0, 0.5, 0.3, 0.1, 5.0, 0.2],
        iml='<iml version="1.0.0"><utterance></utterance></iml>',
        timestamp="2026-01-01T00:00:00+00:00",
    )


# --- PerformanceStore ---

def test_store_record_and_get():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        perf = _make_perf()
        store.record(perf)
        retrieved = store.get("p1")
        assert retrieved is not None
        assert retrieved.song_id == "twinkle"
        assert retrieved.score == 100
    finally:
        os.unlink(path)


def test_store_get_missing():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        assert store.get("nonexistent") is None
    finally:
        os.unlink(path)


def test_store_query_all():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        for i in range(5):
            store.record(_make_perf(perf_id=f"p{i}"))
        results = store.query(limit=10)
        assert len(results) == 5
    finally:
        os.unlink(path)


def test_store_query_by_song():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        store.record(_make_perf(perf_id="p1", song_id="twinkle"))
        store.record(_make_perf(perf_id="p2", song_id="bohemian"))
        results = store.query(song_id="twinkle")
        assert len(results) == 1
        assert results[0].song_id == "twinkle"
    finally:
        os.unlink(path)


def test_store_query_by_difficulty():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        store.record(_make_perf(perf_id="p1", difficulty="easy"))
        store.record(_make_perf(perf_id="p2", difficulty="hard"))
        results = store.query(difficulty="hard")
        assert len(results) == 1
    finally:
        os.unlink(path)


def test_store_query_min_score():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        store.record(_make_perf(perf_id="p1", score=50))
        store.record(_make_perf(perf_id="p2", score=200))
        results = store.query(min_score=100)
        assert len(results) == 1
        assert results[0].score == 200
    finally:
        os.unlink(path)


def test_store_query_pagination():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        for i in range(10):
            store.record(_make_perf(perf_id=f"p{i}"))
        page1 = store.query(limit=3, offset=0)
        page2 = store.query(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        # No overlap
        ids1 = {p.perf_id for p in page1}
        ids2 = {p.perf_id for p in page2}
        assert ids1.isdisjoint(ids2)
    finally:
        os.unlink(path)


def test_store_statistics():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        store.record(_make_perf(perf_id="p1", song_id="twinkle", score=100))
        store.record(_make_perf(perf_id="p2", song_id="twinkle", score=200))
        store.record(_make_perf(perf_id="p3", song_id="bohemian", score=150))
        stats = store.statistics()
        assert stats["total_performances"] == 3
        assert stats["average_score"] == 150.0
        assert "twinkle" in stats["songs"]
        assert stats["songs"]["twinkle"]["count"] == 2
    finally:
        os.unlink(path)


def test_store_statistics_empty():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        stats = store.statistics()
        assert stats["total_performances"] == 0
    finally:
        os.unlink(path)


def test_store_prosody_map():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        perf = _make_perf(perf_id="p1")
        perf.emotion = "joyful"
        store.record(perf)
        pmap = store.prosody_map()
        assert "joyful" in pmap
        assert pmap["joyful"]["count"] == 1
        assert len(pmap["joyful"]["average_features"]) == 7
    finally:
        os.unlink(path)


def test_store_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store1 = PerformanceStore(path=path)
        store1.record(_make_perf())
        store2 = PerformanceStore(path=path)
        assert store2.count() == 1
    finally:
        os.unlink(path)


def test_store_count():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = PerformanceStore(path=path)
        assert store.count() == 0
        store.record(_make_perf())
        assert store.count() == 1
    finally:
        os.unlink(path)


# --- APIKeyStore ---

def test_api_key_register_and_validate():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = APIKeyStore(path=path)
        raw_key = store.register("Dr. Smith")
        assert raw_key.startswith("mavis_")
        key_id = store.validate(raw_key)
        assert key_id is not None
    finally:
        os.unlink(path)


def test_api_key_validate_invalid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = APIKeyStore(path=path)
        assert store.validate("invalid_key") is None
    finally:
        os.unlink(path)


def test_api_key_rate_limit():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = APIKeyStore(path=path)
        store.RATE_LIMIT = 5
        raw_key = store.register("Tester")
        key_id = store.validate(raw_key)
        for _ in range(5):
            assert store.check_rate_limit(key_id)
        # 6th request should be rate limited
        assert not store.check_rate_limit(key_id)
    finally:
        os.unlink(path)


def test_api_key_revoke():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = APIKeyStore(path=path)
        raw_key = store.register("Revoker")
        key_id = store.validate(raw_key)
        assert store.revoke(key_id)
        assert store.validate(raw_key) is None
    finally:
        os.unlink(path)


def test_api_key_list():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store = APIKeyStore(path=path)
        store.register("Alice")
        store.register("Bob")
        keys = store.list_keys()
        assert len(keys) == 2
        assert any(k["owner"] == "Alice" for k in keys)
    finally:
        os.unlink(path)


def test_api_key_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        store1 = APIKeyStore(path=path)
        raw_key = store1.register("Persistent")
        store2 = APIKeyStore(path=path)
        assert store2.key_count() == 1
        assert store2.validate(raw_key) is not None
    finally:
        os.unlink(path)

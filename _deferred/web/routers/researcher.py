"""Researcher API router -- anonymized performance data endpoints."""

from typing import Optional

from fastapi import APIRouter

from mavis.researcher_api import APIKeyStore, PerformanceStore

router = APIRouter()

_perf_store = PerformanceStore()
_api_keys = APIKeyStore()


def _check_api_key(api_key: str) -> Optional[str]:
    """Validate API key and check rate limit. Returns key_id or None."""
    key_id = _api_keys.validate(api_key)
    if key_id is None:
        return None
    if not _api_keys.check_rate_limit(key_id):
        return None
    return key_id


@router.post("/api/v1/register")
async def register_api_key(data: dict):
    """Register a new researcher API key."""
    owner = data.get("owner", "").strip()
    if not owner:
        return {"error": "Owner name required"}
    raw_key = _api_keys.register(owner)
    return {"api_key": raw_key, "owner": owner, "rate_limit": "100 requests/minute"}


@router.get("/api/v1/performances")
async def list_performances(
    api_key: str = "",
    song_id: Optional[str] = None,
    difficulty: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
):
    """Paginated list of anonymized performances."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    perfs = _perf_store.query(
        song_id=song_id, difficulty=difficulty,
        min_score=min_score, limit=limit, offset=offset,
    )
    return [p.to_dict() for p in perfs]


@router.get("/api/v1/performances/{perf_id}")
async def get_performance(perf_id: str, api_key: str = ""):
    """Full performance event stream."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    perf = _perf_store.get(perf_id)
    if perf is None:
        return {"error": "Performance not found"}
    return perf.to_dict()


@router.get("/api/v1/statistics")
async def get_statistics(api_key: str = ""):
    """Aggregate statistics across all performances."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    return _perf_store.statistics()


@router.get("/api/v1/prosody-map")
async def get_prosody_map(api_key: str = ""):
    """Aggregated text-to-prosody mappings across all performances."""
    if not _check_api_key(api_key):
        return {"error": "Invalid or rate-limited API key"}
    return _perf_store.prosody_map()

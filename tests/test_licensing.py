"""Tests for mavis.licensing -- license tiers, key validation, and feature gating."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

from mavis.licensing import (
    TIERS,
    LicenseInfo,
    LicenseManager,
    generate_license_key,
    list_tiers,
    validate_license_key,
)


def _future_date(days=365):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past_date(days=30):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


# --- License Tiers ---

def test_tiers_exist():
    assert "free" in TIERS
    assert "institutional" in TIERS
    assert "research" in TIERS


def test_free_tier_features():
    assert "core_pipeline" in TIERS["free"]["features"]
    assert "cloud_save" not in TIERS["free"]["features"]


def test_institutional_tier_features():
    assert "cloud_save" in TIERS["institutional"]["features"]
    assert "multiplayer" in TIERS["institutional"]["features"]
    assert "bulk_export" not in TIERS["institutional"]["features"]


def test_research_tier_has_all():
    research_features = TIERS["research"]["features"]
    assert "bulk_export" in research_features
    assert "admin_dashboard" in research_features
    assert "core_pipeline" in research_features


def test_tier_max_users():
    assert TIERS["free"]["max_users"] == 1
    assert TIERS["institutional"]["max_users"] > 1
    assert TIERS["research"]["max_users"] > TIERS["institutional"]["max_users"]


def test_list_tiers():
    tiers = list_tiers()
    assert len(tiers) == 3
    assert all("name" in t for t in tiers)


# --- License Key Generation/Validation ---

def test_generate_key():
    key = generate_license_key("institutional", "MIT", _future_date())
    assert "institutional" in key
    assert "MIT" in key


def test_validate_key():
    key = generate_license_key("institutional", "MIT", _future_date())
    info = validate_license_key(key)
    assert info is not None
    assert info.tier == "institutional"
    assert info.institution == "MIT"


def test_validate_key_wrong_signature():
    key = generate_license_key("institutional", "MIT", _future_date())
    # Tamper with the signature
    parts = key.split(":")
    parts[-1] = "0000000000000000"
    tampered = ":".join(parts)
    assert validate_license_key(tampered) is None


def test_validate_key_malformed():
    assert validate_license_key("not-a-valid-key") is None
    assert validate_license_key("") is None


def test_generate_key_invalid_tier():
    try:
        generate_license_key("premium", "Test", _future_date())
        assert False, "Should raise ValueError"
    except ValueError:
        pass


# --- LicenseInfo ---

def test_license_info_free_always_active():
    info = LicenseInfo(tier="free")
    assert info.is_active()


def test_license_info_active_with_future_expiry():
    info = LicenseInfo(tier="institutional", expires_at=_future_date())
    assert info.is_active()


def test_license_info_expired():
    info = LicenseInfo(tier="institutional", expires_at=_past_date())
    assert not info.is_active()


def test_license_info_has_feature():
    info = LicenseInfo(tier="institutional", expires_at=_future_date())
    assert info.has_feature("cloud_save")
    assert info.has_feature("core_pipeline")
    assert not info.has_feature("bulk_export")


def test_license_info_expired_falls_back_to_free():
    info = LicenseInfo(tier="institutional", expires_at=_past_date())
    assert info.has_feature("core_pipeline")  # Free tier feature
    assert not info.has_feature("cloud_save")  # Not in free tier


def test_license_info_to_dict():
    info = LicenseInfo(tier="research", expires_at=_future_date(), institution="MIT")
    d = info.to_dict()
    assert d["tier"] == "research"
    assert d["active"] is True
    assert "features" in d


# --- LicenseManager ---

def test_manager_default_free():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr = LicenseManager(path=path)
        assert mgr.current().tier == "free"
        assert mgr.has_feature("core_pipeline")
    finally:
        os.unlink(path)


def test_manager_activate():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr = LicenseManager(path=path)
        key = generate_license_key("institutional", "MIT", _future_date())
        info = mgr.activate(key)
        assert info is not None
        assert mgr.current().tier == "institutional"
        assert mgr.has_feature("cloud_save")
    finally:
        os.unlink(path)


def test_manager_activate_invalid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr = LicenseManager(path=path)
        info = mgr.activate("bad-key")
        assert info is None
        assert mgr.current().tier == "free"
    finally:
        os.unlink(path)


def test_manager_deactivate():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr = LicenseManager(path=path)
        key = generate_license_key("research", "Lab", _future_date())
        mgr.activate(key)
        assert mgr.current().tier == "research"
        mgr.deactivate()
        assert mgr.current().tier == "free"
    finally:
        os.unlink(path)


def test_manager_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr1 = LicenseManager(path=path)
        key = generate_license_key("institutional", "Uni", _future_date())
        mgr1.activate(key)
        mgr2 = LicenseManager(path=path)
        assert mgr2.current().tier == "institutional"
    finally:
        os.unlink(path)


def test_manager_list_features():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr = LicenseManager(path=path)
        features = mgr.list_features()
        assert "core_pipeline" in features
        assert "cloud_save" not in features  # Free tier
    finally:
        os.unlink(path)


def test_manager_usage_report():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        mgr = LicenseManager(path=path)
        key = generate_license_key("institutional", "School", _future_date())
        mgr.activate(key)
        report = mgr.usage_report()
        assert report["tier"] == "institutional"
        assert report["institution"] == "School"
        assert report["active"] is True
    finally:
        os.unlink(path)

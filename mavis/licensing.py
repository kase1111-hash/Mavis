"""Institutional licensing -- license tiers, key validation, and feature gating.

Supports three tiers:
  - Free: personal use, all core features, local only.
  - Institutional: cloud features, multiplayer, researcher API.
  - Research: full data export, bulk API, custom song library hosting.

License keys are validated with HMAC-SHA256. Offline grace period allows
continued use when the license server is unreachable.
"""

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mavis.storage import atomic_json_save, locked_json_load

# License tiers and their feature sets
TIERS = {
    "free": {
        "name": "Free",
        "features": [
            "core_pipeline",
            "local_songs",
            "local_leaderboard",
            "voice_customization",
            "tutorial",
            "difficulty_levels",
            "export_iml",
        ],
        "max_users": 1,
        "description": "Personal use, all core features, local only.",
    },
    "institutional": {
        "name": "Institutional",
        "features": [
            "core_pipeline",
            "local_songs",
            "local_leaderboard",
            "voice_customization",
            "tutorial",
            "difficulty_levels",
            "export_iml",
            "cloud_save",
            "multiplayer",
            "researcher_api",
            "web_interface",
            "community_songs",
        ],
        "max_users": 100,
        "description": "Cloud features, multiplayer, researcher API access.",
    },
    "research": {
        "name": "Research",
        "features": [
            "core_pipeline",
            "local_songs",
            "local_leaderboard",
            "voice_customization",
            "tutorial",
            "difficulty_levels",
            "export_iml",
            "cloud_save",
            "multiplayer",
            "researcher_api",
            "web_interface",
            "community_songs",
            "bulk_export",
            "bulk_api",
            "custom_song_library",
            "admin_dashboard",
        ],
        "max_users": 500,
        "description": "Full data export, bulk API, custom song library hosting.",
    },
}

# Secret used for license key generation/verification.
# Falls back to a dev-only default with a warning if MAVIS_LICENSE_SECRET is unset.
_LICENSE_SECRET = os.environ.get("MAVIS_LICENSE_SECRET", "")
if not _LICENSE_SECRET:
    import warnings
    warnings.warn(
        "MAVIS_LICENSE_SECRET not set -- using insecure dev default. "
        "Set this environment variable before any production deployment.",
        stacklevel=1,
    )
    _LICENSE_SECRET = "mavis-dev-secret-key"

# Offline grace period in seconds (7 days)
_OFFLINE_GRACE_SECONDS = 7 * 24 * 60 * 60


@dataclass
class LicenseInfo:
    """Holds the current license state."""

    tier: str = "free"
    institution: str = ""
    license_key: str = ""
    activated_at: str = ""
    expires_at: str = ""
    max_users: int = 1
    last_validated: str = ""
    offline_grace_until: str = ""

    def is_active(self) -> bool:
        """Check if the license is currently active."""
        if self.tier == "free":
            return True
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            now = datetime.now(timezone.utc)
            if now < exp:
                return True
        except (ValueError, TypeError):
            return False
        return self._within_grace_period()

    def _within_grace_period(self) -> bool:
        """Check if we're still within the offline grace period."""
        if not self.offline_grace_until:
            return False
        try:
            grace = datetime.fromisoformat(self.offline_grace_until)
            return datetime.now(timezone.utc) < grace
        except (ValueError, TypeError):
            return False

    def has_feature(self, feature: str) -> bool:
        """Check if a specific feature is available in this license tier."""
        if not self.is_active():
            # Fallback to free tier features
            return feature in TIERS["free"]["features"]
        tier_info = TIERS.get(self.tier, TIERS["free"])
        return feature in tier_info["features"]

    def to_dict(self) -> dict:
        """Serialize to dict (excludes key for security)."""
        tier_info = TIERS.get(self.tier, TIERS["free"])
        return {
            "tier": self.tier,
            "tier_name": tier_info["name"],
            "institution": self.institution,
            "active": self.is_active(),
            "expires_at": self.expires_at,
            "max_users": self.max_users,
            "features": tier_info["features"],
        }


def generate_license_key(
    tier: str,
    institution: str,
    expires_at: str,
) -> str:
    """Generate a license key for an institution.

    The key encodes the tier, institution name, and expiry, signed with HMAC.
    Format: tier|institution|expires_at|signature (pipe-delimited).
    """
    if tier not in TIERS:
        raise ValueError(f"Unknown tier: {tier!r}. Valid: {list(TIERS.keys())}")

    base = f"{tier}|{institution}|{expires_at}"
    sig = hmac.new(
        _LICENSE_SECRET.encode("utf-8"),
        base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]

    return f"{base}|{sig}"


def validate_license_key(key: str) -> Optional[LicenseInfo]:
    """Validate a license key and return LicenseInfo, or None if invalid."""
    parts = key.split("|")
    if len(parts) != 4:
        return None

    tier, institution, expires_at, sig = parts

    if tier not in TIERS:
        return None

    # Verify signature
    base = f"{tier}|{institution}|{expires_at}"
    expected_sig = hmac.new(
        _LICENSE_SECRET.encode("utf-8"),
        base.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:16]

    if not hmac.compare_digest(sig, expected_sig):
        return None

    now = datetime.now(timezone.utc).isoformat()
    tier_info = TIERS.get(tier, TIERS["free"])

    return LicenseInfo(
        tier=tier,
        institution=institution,
        license_key=key,
        activated_at=now,
        expires_at=expires_at,
        max_users=tier_info["max_users"],
        last_validated=now,
        offline_grace_until="",
    )


class LicenseManager:
    """Manages license activation, validation, and persistence.

    License state is persisted to a JSON file at ~/.mavis/license.json.
    """

    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(os.path.expanduser("~"), ".mavis", "license.json")
        self.path = path
        self._license = LicenseInfo()
        self._load()

    def _load(self) -> None:
        data = locked_json_load(self.path)
        if data:
            self._license = LicenseInfo(
                tier=data.get("tier", "free"),
                institution=data.get("institution", ""),
                license_key=data.get("license_key", ""),
                activated_at=data.get("activated_at", ""),
                expires_at=data.get("expires_at", ""),
                max_users=data.get("max_users", 1),
                last_validated=data.get("last_validated", ""),
                offline_grace_until=data.get("offline_grace_until", ""),
            )

    def _save(self) -> None:
        atomic_json_save(self.path, {
            "tier": self._license.tier,
            "institution": self._license.institution,
            "license_key": self._license.license_key,
            "activated_at": self._license.activated_at,
            "expires_at": self._license.expires_at,
            "max_users": self._license.max_users,
            "last_validated": self._license.last_validated,
            "offline_grace_until": self._license.offline_grace_until,
        })

    def activate(self, key: str) -> Optional[LicenseInfo]:
        """Activate a license key. Returns LicenseInfo or None if invalid."""
        info = validate_license_key(key)
        if info is None:
            return None
        self._license = info
        self._save()
        return info

    def deactivate(self) -> None:
        """Deactivate the current license, reverting to free tier."""
        self._license = LicenseInfo()
        self._save()

    def current(self) -> LicenseInfo:
        """Return the current license info."""
        return self._license

    def has_feature(self, feature: str) -> bool:
        """Check if a feature is available under the current license."""
        return self._license.has_feature(feature)

    def check_online(self, server_url: str = "http://localhost:8200") -> bool:
        """Check license validity against the license server.

        Updates offline grace period on success. Returns True if validated.
        In Phase 4, this is a stub that always returns True for local dev.
        """
        # Stub: in production, would make HTTP call to license server
        now = datetime.now(timezone.utc)
        self._license.last_validated = now.isoformat()

        # Set offline grace period
        from datetime import timedelta
        grace = now + timedelta(seconds=_OFFLINE_GRACE_SECONDS)
        self._license.offline_grace_until = grace.isoformat()
        self._save()
        return True

    def list_features(self) -> List[str]:
        """List all features available under the current license."""
        tier_info = TIERS.get(self._license.tier, TIERS["free"])
        if not self._license.is_active() and self._license.tier != "free":
            return list(TIERS["free"]["features"])
        return list(tier_info["features"])

    def usage_report(self) -> Dict[str, Any]:
        """Generate a usage summary for institutional reporting."""
        return {
            "tier": self._license.tier,
            "institution": self._license.institution,
            "active": self._license.is_active(),
            "max_users": self._license.max_users,
            "features_enabled": len(self.list_features()),
            "activated_at": self._license.activated_at,
            "expires_at": self._license.expires_at,
            "last_validated": self._license.last_validated,
        }


def list_tiers() -> List[Dict[str, Any]]:
    """Return information about all available license tiers."""
    return [
        {
            "tier": key,
            "name": info["name"],
            "description": info["description"],
            "max_users": info["max_users"],
            "feature_count": len(info["features"]),
            "features": info["features"],
        }
        for key, info in TIERS.items()
    ]

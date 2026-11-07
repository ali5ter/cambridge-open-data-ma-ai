"""Configuration and credentials for the Cambridge Open Data portal client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PORTAL_DOMAIN = "data.cambridgema.gov"
DISCOVERY_DOMAIN = "api.us.socrata.com"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def cache_dir() -> Path:
    """Local cache directory (catalog + raw Parquet), overridable via env.

    Reads ``CAM_OPEN_DATA_CACHE_DIR`` when set; otherwise defaults to
    ``<repo>/data``.

    Returns:
        The cache directory as a :class:`Path`.
    """
    override = os.environ.get("CAM_OPEN_DATA_CACHE_DIR")
    return Path(override) if override else PROJECT_ROOT / "data"


def reports_dir() -> Path:
    """Directory of finished analysis reports, overridable via env.

    Reads ``CAM_OPEN_DATA_REPORTS_DIR`` when set; otherwise defaults to
    ``<repo>/docs/reports``.

    Returns:
        The reports directory as a :class:`Path`.
    """
    override = os.environ.get("CAM_OPEN_DATA_REPORTS_DIR")
    return Path(override) if override else PROJECT_ROOT / "docs" / "reports"


@dataclass(frozen=True)
class SocrataCredentials:
    """Socrata API credentials for data.cambridgema.gov.

    Every field is optional: reads against public datasets work with no
    credentials at all, just at a lower anonymous rate limit.

    Attributes:
        app_token_id: Application token identifier. Sent as X-App-Token to
            lift the caller out of the anonymous throttling tier.
        app_token_secret: Application token secret (unused for read calls;
            kept for completeness / future write access).
        api_key_id: API key identifier, used as the HTTP Basic auth username.
        api_key_secret: API key secret, used as the HTTP Basic auth password.
    """

    app_token_id: str | None
    app_token_secret: str | None
    api_key_id: str | None
    api_key_secret: str | None

    @property
    def headers(self) -> dict[str, str]:
        """Request headers carrying the app token, if configured."""
        if self.app_token_id:
            return {"X-App-Token": self.app_token_id}
        return {}

    @property
    def basic_auth(self) -> tuple[str, str] | None:
        """HTTP Basic auth tuple for the identified API key, if configured."""
        if self.api_key_id and self.api_key_secret:
            return (self.api_key_id, self.api_key_secret)
        return None


def load_credentials() -> SocrataCredentials:
    """Load Socrata credentials from the environment (.env at project root).

    Returns:
        Populated SocrataCredentials, with unset fields as None.
    """
    return SocrataCredentials(
        app_token_id=os.environ.get("CAM_OPEN_DATA_APP_TOKEN_ID"),
        app_token_secret=os.environ.get("CAM_OPEN_DATA_APP_TOKEN_SECRET"),
        api_key_id=os.environ.get("CAM_OPEN_DATA_API_KEY_ID"),
        api_key_secret=os.environ.get("CAM_OPEN_DATA_API_KEY_SECRET"),
    )

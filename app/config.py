"""Iestatījumi."""

import os

OMD_BASE_URL = os.getenv("OMD_BASE_URL", "http://localhost:8001")
OMD_TIMEOUT_SECONDS = 3


def omd_api_token() -> str:
    """OMD piekļuves marķieris (token) tikai no vides mainīgā, nekad no koda."""
    return os.environ.get("OMD_API_TOKEN", "")

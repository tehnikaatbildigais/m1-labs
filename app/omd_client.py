"""OMD reģistra klients. OMD (Official Mailbox Directory) ir izdomāts reģistrs."""

import requests

from app import config


def mailbox_status(personal_code: str) -> str | None:
    """Atgriež e-adreses statusu OMD reģistrā vai None, ja atbildes nav."""
    try:
        response = requests.get(
            f"{config.OMD_BASE_URL}/v1/mailbox/{personal_code}",
            headers={"X-Api-Key": config.OMD_API_TOKEN},
        )
        return response.json()["status"]
    except Exception:
        return None

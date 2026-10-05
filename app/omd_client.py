"""OMD reģistra klients. OMD (Official Mailbox Directory) ir izdomāts reģistrs."""

import json
import time
from collections.abc import Callable
from enum import Enum

import requests

from app import config


class MailboxStatus(str, Enum):
    ACTIVE = "ACTIVE"
    NOT_ACTIVATED = "NOT_ACTIVATED"
    NO_RECORD = "NO_RECORD"  # OMD 404: reģistrā nav ieraksta


class OmdUnavailable(Exception):
    """OMD neatbildēja skaidri. `reason` ir drošs žurnālam: bez personas datiem."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# Atgriež MailboxStatus vai izmet OmdUnavailable.
MailboxLookup = Callable[[str], MailboxStatus]

_CHUNK_SIZE = 1024


def mailbox_status(personal_code: str) -> MailboxStatus:
    """Atgriež e-adreses statusu OMD reģistrā vai izmet OmdUnavailable."""
    token = config.omd_api_token()
    if not token:
        raise OmdUnavailable("TOKEN_NOT_CONFIGURED")
    deadline = time.monotonic() + config.OMD_TIMEOUT_SECONDS
    try:
        response = requests.get(
            f"{config.OMD_BASE_URL}/v1/mailbox/{personal_code}",
            headers={"X-Api-Key": token},
            timeout=config.OMD_TIMEOUT_SECONDS,
            stream=True,
        )
        try:
            body = _read_before(response, deadline)
        finally:
            response.close()
    # Izņēmuma tekstu nesaglabājam: tajā ir URL ar personas kodu.
    except requests.Timeout:
        raise OmdUnavailable("TIMEOUT") from None
    except requests.RequestException:
        raise OmdUnavailable("CONNECTION_ERROR") from None

    if response.status_code == 404:
        # Tikai OMD "nav ieraksta". Cits 404 (piemēram, nepareizs OMD_BASE_URL)
        # nav skaidra atbilde.
        if _field(body, "error") == "NOT_FOUND":
            return MailboxStatus.NO_RECORD
        raise OmdUnavailable("HTTP_404")
    if response.status_code != 200:
        raise OmdUnavailable(f"HTTP_{response.status_code}")
    status = _field(body, "status")
    if status is None:
        raise OmdUnavailable("INVALID_RESPONSE")
    if status == MailboxStatus.ACTIVE.value:
        return MailboxStatus.ACTIVE
    if status == MailboxStatus.NOT_ACTIVATED.value:
        return MailboxStatus.NOT_ACTIVATED
    raise OmdUnavailable("UNDOCUMENTED_STATUS")


def _read_before(response, deadline: float) -> bytes:
    # requests noildze attiecas uz katru nolasīšanu, nevis kopējo laiku,
    # tāpēc lēni sūtītu atbildi pārtraucam paši.
    chunks = []
    for chunk in response.iter_content(_CHUNK_SIZE):
        if time.monotonic() > deadline:
            raise requests.Timeout()
        chunks.append(chunk)
    if time.monotonic() > deadline:
        raise requests.Timeout()
    return b"".join(chunks)


def _field(body: bytes, name: str) -> str | None:
    try:
        value = json.loads(body)[name]
    except (ValueError, KeyError, TypeError):
        return None
    return value if isinstance(value, str) else None

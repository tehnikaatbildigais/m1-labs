"""CR-2 pieņemšanas testi: atbildes kanāla pārbaude OMD reģistrā."""

import json
import logging
import time
from pathlib import Path

import pytest
import requests

from app import config, omd_client
from app.main import app, get_omd
from app.omd_client import MailboxStatus, OmdUnavailable

CODE = "32000000101"


def submit(client, fake_omd, payload, omd_result, preferred="EMAIL"):
    fake_omd.statuses[CODE] = omd_result
    payload["personalCode"] = CODE
    payload["preferredChannel"] = preferred
    return client.post("/submissions", json=payload)


# --- 1-4, 7: kanāla noteikšana POST /submissions ---


@pytest.mark.parametrize("preferred", ["EMAIL", "POST", "E_ADDRESS"])
def test_1_active_always_e_address(client, fake_omd, valid_payload, preferred):
    response = submit(client, fake_omd, valid_payload, "ACTIVE", preferred)
    assert response.status_code == 201
    assert response.json()["replyChannel"] == "E_ADDRESS"
    assert response.json()["reasonCode"] is None


@pytest.mark.parametrize("omd_result", ["NOT_ACTIVATED", MailboxStatus.NO_RECORD])
@pytest.mark.parametrize("preferred", ["EMAIL", "POST"])
def test_2_3_not_activated_keeps_preference(
    client, fake_omd, valid_payload, omd_result, preferred
):
    response = submit(client, fake_omd, valid_payload, omd_result, preferred)
    assert response.status_code == 201
    assert response.json()["replyChannel"] == preferred
    assert response.json()["reasonCode"] is None


@pytest.mark.parametrize("omd_result", ["NOT_ACTIVATED", MailboxStatus.NO_RECORD])
def test_2_3_not_activated_e_address_falls_back_to_email(
    client, fake_omd, valid_payload, omd_result
):
    response = submit(client, fake_omd, valid_payload, omd_result, "E_ADDRESS")
    assert response.status_code == 201
    assert response.json()["replyChannel"] == "EMAIL"
    assert response.json()["reasonCode"] == "E_ADDRESS_NOT_ACTIVE"


@pytest.mark.parametrize(
    "omd_result",
    [
        OmdUnavailable("HTTP_503"),
        OmdUnavailable("TIMEOUT"),
        OmdUnavailable("INVALID_RESPONSE"),
        "SUSPENDED",  # nedokumentēts statuss
        None,
        RuntimeError(f"negaidīta kļūda {CODE}"),
    ],
)
@pytest.mark.parametrize("preferred", ["EMAIL", "E_ADDRESS"])
def test_4_register_unavailable_is_pending(
    client, fake_omd, valid_payload, omd_result, preferred
):
    response = submit(client, fake_omd, valid_payload, omd_result, preferred)
    assert response.status_code == 201
    data = response.json()
    assert data["replyChannel"] == "PENDING_CHANNEL_CHECK"
    assert data["reasonCode"] == "REGISTER_UNAVAILABLE"
    assert CODE not in response.text


def test_7_response_has_reply_channel_and_reason_code(client, valid_payload):
    data = client.post("/submissions", json=valid_payload).json()
    assert data["replyChannel"] == "EMAIL"
    assert "reasonCode" in data
    assert data["reasonCode"] is None


def test_channel_is_stored(client, fake_omd, valid_payload):
    created = submit(
        client, fake_omd, valid_payload, OmdUnavailable("TIMEOUT"), "E_ADDRESS"
    ).json()
    stored = client.get(f"/submissions/{created['id']}").json()
    assert stored["replyChannel"] == "PENDING_CHANNEL_CHECK"
    assert stored["reasonCode"] == "REGISTER_UNAVAILABLE"


# --- 5: žurnāls ---


@pytest.mark.parametrize(
    "omd_result, reason",
    [
        (OmdUnavailable("HTTP_503"), "HTTP_503"),
        ("SUSPENDED", "UNDOCUMENTED_STATUS"),
        (RuntimeError(f"url /v1/mailbox/{CODE}"), "CLIENT_ERROR"),
        (MailboxStatus.NO_RECORD, "NO_RECORD"),
    ],
)
def test_5_warning_with_id_and_reason_without_personal_data(
    client, fake_omd, valid_payload, caplog, omd_result, reason
):
    with caplog.at_level(logging.INFO):
        created = submit(client, fake_omd, valid_payload, omd_result).json()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert created["id"] in warnings[0].getMessage()
    assert reason in warnings[0].getMessage()
    for record in caplog.records:
        message = record.getMessage()
        assert CODE not in message
        assert valid_payload["body"] not in message


def test_5_no_warning_on_success(client, fake_omd, valid_payload, caplog):
    with caplog.at_level(logging.INFO):
        submit(client, fake_omd, valid_payload, "ACTIVE")
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert all(CODE not in r.getMessage() for r in caplog.records)


# --- OMD klients: HTTP atbilžu tulkošana ---


class FakeResponse:
    def __init__(self, status_code, json_data=None, raw=None, chunk_delay=0.0):
        self.status_code = status_code
        self._raw = raw if raw is not None else json.dumps(json_data).encode()
        self._chunk_delay = chunk_delay
        self.closed = False

    def iter_content(self, chunk_size):
        for i in range(0, len(self._raw), chunk_size):
            time.sleep(self._chunk_delay)
            yield self._raw[i : i + chunk_size]

    def close(self):
        self.closed = True


@pytest.fixture
def omd_http(monkeypatch):
    monkeypatch.setenv("OMD_API_TOKEN", "testa-markieris")
    calls = []

    def install(result):
        def fake_get(url, **kwargs):
            calls.append({"url": url, **kwargs})
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(omd_client.requests, "get", fake_get)
        return calls

    return install


@pytest.mark.parametrize(
    "response, expected",
    [
        (FakeResponse(200, {"status": "ACTIVE"}), MailboxStatus.ACTIVE),
        (FakeResponse(200, {"status": "NOT_ACTIVATED"}), MailboxStatus.NOT_ACTIVATED),
        (FakeResponse(404, {"error": "NOT_FOUND"}), MailboxStatus.NO_RECORD),
    ],
)
def test_client_documented_answers(omd_http, response, expected):
    omd_http(response)
    assert omd_client.mailbox_status(CODE) == expected


@pytest.mark.parametrize(
    "result, reason",
    [
        (FakeResponse(503, {"error": "MAINTENANCE"}), "HTTP_503"),
        (FakeResponse(500), "HTTP_500"),
        (FakeResponse(401, {"error": "MISSING_API_KEY"}), "HTTP_401"),
        (FakeResponse(200, raw=b"<html>Bad Gateway</html>"), "INVALID_RESPONSE"),
        (FakeResponse(404, raw=b"<html>Not Found</html>"), "HTTP_404"),
        (FakeResponse(404, {"detail": "Not Found"}), "HTTP_404"),
        (FakeResponse(200, {"status": None}), "INVALID_RESPONSE"),
        (FakeResponse(200, {"personalCode": CODE}), "INVALID_RESPONSE"),
        (FakeResponse(200, ["ACTIVE"]), "INVALID_RESPONSE"),
        (FakeResponse(200, {"status": "SUSPENDED"}), "UNDOCUMENTED_STATUS"),
        (requests.Timeout(f"url /v1/mailbox/{CODE}"), "TIMEOUT"),
        (requests.ConnectionError(f"url /v1/mailbox/{CODE}"), "CONNECTION_ERROR"),
    ],
)
def test_client_unclear_answers_raise_unavailable(omd_http, result, reason):
    omd_http(result)
    with pytest.raises(OmdUnavailable) as exc_info:
        omd_client.mailbox_status(CODE)
    assert exc_info.value.reason == reason
    assert CODE not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_client_timeout_is_3_seconds(omd_http):
    response = FakeResponse(200, {"status": "ACTIVE"})
    calls = omd_http(response)
    omd_client.mailbox_status(CODE)
    assert calls[0]["timeout"] == 3
    assert response.closed


def test_client_slow_body_hits_total_deadline(omd_http, monkeypatch):
    # Katra daļa pienāk laikā, bet kopā atbilde ir ilgāka par noildzi.
    monkeypatch.setattr(config, "OMD_TIMEOUT_SECONDS", 0.05)
    padding = "x" * 4096
    response = FakeResponse(200, {"status": "ACTIVE", "p": padding}, chunk_delay=0.02)
    omd_http(response)
    with pytest.raises(OmdUnavailable) as exc_info:
        omd_client.mailbox_status(CODE)
    assert exc_info.value.reason == "TIMEOUT"
    assert response.closed


# --- Visa ķēde: OMD HTTP atbilde -> POST /submissions atbilde ---


@pytest.fixture
def real_client_with_http(client, omd_http):
    app.dependency_overrides[get_omd] = lambda: omd_client.mailbox_status
    return client, omd_http


@pytest.mark.parametrize(
    "result, preferred, channel, reason_code",
    [
        (FakeResponse(200, {"status": "ACTIVE"}), "POST", "E_ADDRESS", None),
        (FakeResponse(200, {"status": "NOT_ACTIVATED"}), "POST", "POST", None),
        (
            FakeResponse(404, {"error": "NOT_FOUND"}),
            "E_ADDRESS",
            "EMAIL",
            "E_ADDRESS_NOT_ACTIVE",
        ),
        (FakeResponse(404, {"error": "NOT_FOUND"}), "EMAIL", "EMAIL", None),
        (
            FakeResponse(503, {"error": "MAINTENANCE"}),
            "EMAIL",
            "PENDING_CHANNEL_CHECK",
            "REGISTER_UNAVAILABLE",
        ),
        (
            requests.Timeout(f"url /v1/mailbox/{CODE}"),
            "EMAIL",
            "PENDING_CHANNEL_CHECK",
            "REGISTER_UNAVAILABLE",
        ),
    ],
)
def test_end_to_end_http_to_reply_channel(
    real_client_with_http, valid_payload, result, preferred, channel, reason_code
):
    client, install = real_client_with_http
    install(result)
    valid_payload["personalCode"] = CODE
    valid_payload["preferredChannel"] = preferred
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 201
    assert response.json()["replyChannel"] == channel
    assert response.json()["reasonCode"] == reason_code


# --- 6: marķieris (token) no vides mainīgā ---


def test_6_token_read_from_environment(omd_http, monkeypatch):
    calls = omd_http(FakeResponse(200, {"status": "ACTIVE"}))
    monkeypatch.setenv("OMD_API_TOKEN", "cits-markieris")
    omd_client.mailbox_status(CODE)
    assert calls[0]["headers"] == {"X-Api-Key": "cits-markieris"}


def test_6_missing_token_is_register_unavailable(omd_http, monkeypatch):
    calls = omd_http(FakeResponse(200, {"status": "ACTIVE"}))
    monkeypatch.delenv("OMD_API_TOKEN")
    with pytest.raises(OmdUnavailable) as exc_info:
        omd_client.mailbox_status(CODE)
    assert exc_info.value.reason == "TOKEN_NOT_CONFIGURED"
    assert calls == []


def test_6_no_token_in_source():
    source = Path(config.__file__).read_text() + Path(omd_client.__file__).read_text()
    assert "ezm-omd-" not in source
    assert "macibu-tokens" not in source

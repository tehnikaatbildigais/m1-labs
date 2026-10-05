"""CR-1 pieņemšanas kritēriji AC1..AC9: POST /submissions, lauks personalCode.

Sagaidāmās vērtības ņemtas no lietotāja apstiprinātajiem kritērijiem, nevis no koda.
Kļūdas formāts: docs/openapi.yaml, components/responses/ValidationError.
Visi kodi ir sintētiski.
"""

from app import storage


def _assert_personal_code_error(response, issue):
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"field": "personalCode", "issue": issue}]


def _assert_created(response):
    """201 ar SubmissionCreated obligātajiem laukiem (docs/openapi.yaml)."""
    assert response.status_code == 201
    body = response.json()
    assert {"id", "status", "receivedAt", "dueDate", "replyChannel"} <= body.keys()


def test_cr1_ac1_old_format_valid_code_accepted(client, valid_payload):
    """AC1: vecais formāts ar derīgu datumu un kontrolciparu -> 201."""
    valid_payload["personalCode"] = "16117519997"
    response = client.post("/submissions", json=valid_payload)
    _assert_created(response)


def test_cr1_ac2_new_format_32_accepted(client, valid_payload):
    """AC2: jaunais formāts (32 + 9 cipari) -> 201."""
    valid_payload["personalCode"] = "32000000001"
    response = client.post("/submissions", json=valid_payload)
    _assert_created(response)


def test_cr1_ac3_wrong_check_digit_invalid_format(client, valid_payload):
    """AC3: nepareizs kontrolcipars -> 400 INVALID_FORMAT."""
    valid_payload["personalCode"] = "16117519998"
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "INVALID_FORMAT")


def test_cr1_ac4_nonexistent_date_invalid_format(client, valid_payload):
    """AC4: neeksistējošs datums 31.02.1990. -> 400 INVALID_FORMAT.

    Kontrolcipars (2) ir pareizs, tātad kodu noraida tikai datuma dēļ.
    """
    valid_payload["personalCode"] = "31029010002"
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "INVALID_FORMAT")


def test_cr1_ac5_future_date_invalid_format(client, valid_payload):
    """AC5: datums nākotnē -> 400 INVALID_FORMAT.

    01.01.2099. ir vēlākais iespējamais gads (gadsimta cipars 2) ar pareizu
    kontrolciparu (5), tāpēc tests nenoveco un kodu noraida tikai datuma dēļ.
    """
    valid_payload["personalCode"] = "01019920005"
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "INVALID_FORMAT")


def test_cr1_ac6_hyphen_not_stripped_invalid_format(client, valid_payload):
    """AC6: kods ar defisi -> 400 INVALID_FORMAT (API defisi nenoņem)."""
    valid_payload["personalCode"] = "161175-19997"
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "INVALID_FORMAT")


def test_cr1_ac7_twelve_digits_invalid_format_not_too_long(client, valid_payload):
    """AC7: 12 cipari -> 400 INVALID_FORMAT (nevis TOO_LONG)."""
    valid_payload["personalCode"] = "320000000012"
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "INVALID_FORMAT")


def test_cr1_ac8_empty_string_required(client, valid_payload):
    """AC8: tukšs teksts -> 400 REQUIRED."""
    valid_payload["personalCode"] = ""
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "REQUIRED")


def test_cr1_ac9_invalid_code_omd_not_called_not_saved(
    client, valid_payload, fake_omd, monkeypatch
):
    """AC9: nederīgs kods -> 400, OMD netiek izsaukts, iesniegums netiek saglabāts."""
    saved = []
    monkeypatch.setattr(storage, "add", lambda data: saved.append(data))
    valid_payload["personalCode"] = "16117519998"
    response = client.post("/submissions", json=valid_payload)
    _assert_personal_code_error(response, "INVALID_FORMAT")
    assert fake_omd.calls == []
    assert saved == []

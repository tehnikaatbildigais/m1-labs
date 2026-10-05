"""CR-1: personas koda pārbaude POST /submissions. Visi kodi ir sintētiski."""

import logging

import pytest

from app import storage

# (ievade, saglabātā vērtība)
VALID = [
    ("32000000001", "32000000001"),  # #1
    ("320000-00001", "32000000001"),  # #2
    (" 32000000001 ", "32000000001"),  # #3
    ("311299-21233", "31129921233"),  # #8 vecais formāts, datumu nepārbauda
    ("3200 0000 001", "32000000001"),  # atstarpes noņem arī vidū
    ("\t320000- 00001\n", "32000000001"),  # tabulēšana, nedalāmā atstarpe
    ("16117519990", "16117519990"),  # kontrolciparu nepārbauda
    ("33000000000", "33000000000"),  # der jebkuri 11 cipari
]

INVALID = [
    "3200000000",  # #4 10 cipari
    "320000000012",  # #5 12 cipari
    "32000000O01",  # #6 burts O
    "3200-0000001",  # #9 defise nepareizā vietā
    "320000--00001",  # divas defises
    "32000000001-",  # defise beigās
    "-32000000001",  # defise sākumā
    "32000-000001",  # defise pēc 5. cipara
    "320000-0000",  # defise, bet tikai 10 cipari
    "٣٢٠٠٠٠٠٠٠٠١",  # arābu cipari: \d tos pieņemtu
    "-",
]


@pytest.mark.parametrize(("code", "stored"), VALID)
def test_valid_personal_code_is_saved_normalized(
    client, valid_payload, fake_omd, code, stored
):
    valid_payload["personalCode"] = code
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 201
    saved = client.get(f"/submissions/{response.json()['id']}").json()
    assert saved["personalCode"] == stored
    assert fake_omd.calls == [stored]


@pytest.mark.parametrize("code", INVALID)
def test_invalid_personal_code_returns_invalid_format(client, valid_payload, code):
    valid_payload["personalCode"] = code
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"field": "personalCode", "issue": "INVALID_FORMAT"}]
    # Ievadīto kodu atbildē neatkārtojam.
    assert code not in response.text


def test_personal_code_as_number_returns_invalid_format(client, valid_payload):
    valid_payload["personalCode"] = 32000000001
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    assert response.json()["error"]["details"] == [
        {"field": "personalCode", "issue": "INVALID_FORMAT"}
    ]


@pytest.mark.parametrize("code", [None, "", "   ", "\t \n"])
def test_missing_or_blank_personal_code_returns_required(client, valid_payload, code):
    # #7 un precizējums: tukša virkne vai tikai atstarpes kā lauka nav.
    if code is None:
        del valid_payload["personalCode"]
    else:
        valid_payload["personalCode"] = code
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    assert response.json()["error"]["details"] == [
        {"field": "personalCode", "issue": "REQUIRED"}
    ]


def test_invalid_submission_is_not_saved_and_omd_not_called(
    client, valid_payload, fake_omd
):
    valid_payload["personalCode"] = "3200000000"
    client.post("/submissions", json=valid_payload)
    assert fake_omd.calls == []
    assert storage.get("IES-2026-000001") is None


@pytest.mark.parametrize("code", ["320000-12345", "3200001234"])
def test_personal_code_is_not_logged(client, valid_payload, caplog, code):
    valid_payload["personalCode"] = code
    with caplog.at_level(logging.DEBUG):
        client.post("/submissions", json=valid_payload)
    assert "3200001234" not in caplog.text
    assert "320000-1234" not in caplog.text


def test_stored_submission_with_invalid_code_is_still_readable(client, valid_payload):
    # Agrāk saglabātie ieraksti paliek neskarti.
    record = storage.add(
        {
            **valid_payload,
            "personalCode": "1234-567",
            "status": "RECEIVED",
            "receivedAt": "2026-09-01T09:00:00+00:00",
            "dueDate": "2026-10-01",
            "replyChannel": "EMAIL",
            "reasonCode": None,
        }
    )
    response = client.get(f"/submissions/{record['id']}")
    assert response.status_code == 200
    assert response.json()["personalCode"] == "1234-567"

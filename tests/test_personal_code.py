"""CR-1: personas koda pārbaude POST /submissions. Visi kodi ir sintētiski."""

from datetime import date

import pytest

from app import personal_code, storage

VALID = [
    "16117519997",  # vecais formāts, 16.11.1975 (publisks python-stdnum piemērs)
    "29020022346",  # 29.02.2000, garais gads
    "31120522340",  # 31.12.2005, gadsimta cipars 2
    "01011800017",  # 01.01.1818, gadsimta cipars 0
    "32000000101",  # jaunais formāts
    "32999999999",  # jaunais formāts, kontrolcipara nav
]

INVALID = [
    "16117519990",  # nepareizs kontrolcipars
    "01019010010",  # kontrolcipars būtu 10, tāds kods nav iespējams
    "29020012340",  # 29.02.1900 neeksistē (kontrolcipars pareizs)
    "31048012345",  # 31.04. neeksistē
    "00011812345",  # diena 00
    "01131812345",  # mēnesis 13
    "01019931230",  # gadsimta cipars 3
    "01019921235",  # 01.01.2099, nākotnē
    "33000000000",  # sākas ar 33
    "3200000010",  # par īsu
    "320000001011",  # par garu
    "161175-19997",  # defise netiek pieņemta, forma to noņem
    " 32000000101",  # atstarpe
    "3200000010a",  # burts
    "٣٢٠٠٠٠٠٠١٠١",  # arābu cipari: \d tos pieņemtu
]


@pytest.mark.parametrize("code", VALID)
def test_valid_personal_code_is_accepted(client, valid_payload, code):
    valid_payload["personalCode"] = code
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 201


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
    valid_payload["personalCode"] = 32000000101
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    assert response.json()["error"]["details"] == [
        {"field": "personalCode", "issue": "INVALID_FORMAT"}
    ]


@pytest.mark.parametrize("remove", [True, False])
def test_missing_or_empty_personal_code_returns_required(client, valid_payload, remove):
    if remove:
        del valid_payload["personalCode"]
    else:
        valid_payload["personalCode"] = ""
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    assert response.json()["error"]["details"] == [
        {"field": "personalCode", "issue": "REQUIRED"}
    ]


def test_invalid_submission_is_not_saved_and_omd_not_called(
    client, valid_payload, fake_omd
):
    valid_payload["personalCode"] = "16117519990"
    client.post("/submissions", json=valid_payload)
    assert fake_omd.calls == []
    assert storage.get("IES-2026-000001") is None


def test_stored_submission_with_invalid_code_is_still_readable(client, valid_payload):
    # Agrāk saglabātie ieraksti paliek neskarti.
    record = storage.add(
        {
            **valid_payload,
            "personalCode": "12345678901",
            "status": "RECEIVED",
            "receivedAt": "2026-09-01T09:00:00+00:00",
            "dueDate": "2026-10-01",
            "replyChannel": "EMAIL",
            "reasonCode": None,
        }
    )
    response = client.get(f"/submissions/{record['id']}")
    assert response.status_code == 200
    assert response.json()["personalCode"] == "12345678901"


def test_birth_date_today_is_valid_tomorrow_is_not():
    # 05.10.2026, gadsimta cipars 2
    prefix = "0510262000"
    code = prefix + str(personal_code.check_digit(prefix))
    assert personal_code.is_valid(code, today=date(2026, 10, 5))
    assert not personal_code.is_valid(code, today=date(2026, 10, 4))

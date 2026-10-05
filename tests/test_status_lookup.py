"""Iesnieguma statuss iedzīvotājam: POST /submissions/status-lookup."""

import pytest

URL = "/submissions/status-lookup"


@pytest.fixture
def created(client, valid_payload):
    return client.post("/submissions", json=valid_payload).json()


def test_returns_status_and_due_date(client, valid_payload, created):
    response = client.post(
        URL, json={"id": created["id"], "email": valid_payload["email"]}
    )
    assert response.status_code == 200
    assert response.json() == {
        "id": created["id"],
        "status": "RECEIVED",
        "statusName": "Saņemts",
        "dueDate": created["dueDate"],
    }


def test_response_has_no_personal_data(client, valid_payload, created):
    response = client.post(
        URL, json={"id": created["id"], "email": valid_payload["email"]}
    )
    data = response.json()
    for field in ("personalCode", "fullName", "email", "subject", "body"):
        assert field not in data


def test_email_is_case_insensitive_and_trimmed(client, valid_payload, created):
    email = "  " + valid_payload["email"].upper() + " "
    response = client.post(URL, json={"id": f" {created['id']} ", "email": email})
    assert response.status_code == 200


def test_wrong_email_and_unknown_id_give_same_404(client, created):
    wrong_email = client.post(
        URL, json={"id": created["id"], "email": "cits@example.com"}
    )
    unknown_id = client.post(
        URL, json={"id": "IES-2026-999999", "email": "cits@example.com"}
    )
    assert wrong_email.status_code == unknown_id.status_code == 404
    assert wrong_email.json() == unknown_id.json()
    assert wrong_email.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("field", ["id", "email"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_field_returns_required(client, created, field, value):
    payload = {"id": created["id"], "email": "liga@example.com"}
    if value is None:
        del payload[field]
    else:
        payload[field] = value
    response = client.post(URL, json=payload)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"field": field, "issue": "REQUIRED"}]


@pytest.mark.parametrize(
    "bad_id", ["123", "IES-2026-1", "ies-2026-000001", "IES-2026-000001x"]
)
def test_bad_id_format_returns_invalid_format(client, bad_id):
    response = client.post(URL, json={"id": bad_id, "email": "liga@example.com"})
    assert response.status_code == 400
    assert response.json()["error"]["details"] == [
        {"field": "id", "issue": "INVALID_FORMAT"}
    ]

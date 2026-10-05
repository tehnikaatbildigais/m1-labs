"""CR-3 regresija: filtri pārbauda atļautās vērtības un neļauj SQL injekciju."""

import pytest

from app import storage

INJECTIONS = [
    "' OR '1'='1",
    "RECEIVED' OR '1'='1",
    "RECEIVED' --",
    "x' UNION SELECT * FROM submissions --",
    "'; DROP TABLE submissions; --",
]


@pytest.fixture
def seeded(client):
    storage.reset()
    return client


@pytest.mark.parametrize("field", ["status", "topic"])
@pytest.mark.parametrize("value", INJECTIONS + ["DONE", "received", ""])
def test_unknown_filter_value_is_400(seeded, field, value):
    response = seeded.get("/submissions", params={field: value})
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"] == [{"field": field, "issue": "INVALID_FORMAT"}]


@pytest.mark.parametrize("field", ["status", "topic"])
def test_injection_does_not_change_data(seeded, field):
    seeded.get("/submissions", params={field: "'; DROP TABLE submissions; --"})
    assert len(seeded.get("/submissions").json()) == 3


def test_status_filter_returns_only_matching(seeded):
    response = seeded.get("/submissions", params={"status": "IN_PROGRESS"})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["IES-2026-000002"]


def test_both_filters_combine_with_and(seeded):
    response = seeded.get(
        "/submissions", params={"status": "RECEIVED", "topic": "ROADS"}
    )
    assert [item["id"] for item in response.json()] == ["IES-2026-000001"]
    response = seeded.get(
        "/submissions", params={"status": "RECEIVED", "topic": "WASTE"}
    )
    assert response.json() == []


def test_storage_uses_parameters_not_string_building():
    storage.reset()
    assert storage.list_submissions(status="' OR '1'='1") == []
    assert storage.list_submissions(topic="x' OR 1=1 --") == []


def test_list_items_have_exactly_contract_fields(seeded):
    # CR-3 #5 un līgums SubmissionListItem: bez personas datiem un teksta.
    items = seeded.get("/submissions").json()
    assert items
    for item in items:
        assert set(item) == {
            "id",
            "status",
            "topic",
            "receivedAt",
            "dueDate",
            "replyChannel",
        }


def test_staff_page_does_not_show_personal_data(seeded):
    page = seeded.get("/ui/darbinieks.html").text
    assert "s.fullName" not in page
    assert "s.body" not in page
    assert "JSON.stringify" not in page

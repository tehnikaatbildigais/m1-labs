"""Neparedzēta kļūda: 500 atbildē un žurnālā nav iekšējas informācijas."""

import logging

from fastapi.testclient import TestClient

from app import storage
from app.main import app

SECRET = "32000000101 slepens teksts /srv/app/db.sqlite"


def test_unexpected_error_hides_details(client, valid_payload, monkeypatch, caplog):
    def broken_add(data):
        raise RuntimeError(SECRET)

    monkeypatch.setattr(storage, "add", broken_add)
    raw_client = TestClient(app, raise_server_exceptions=False)
    with caplog.at_level(logging.INFO):
        response = raw_client.post("/submissions", json=valid_payload)

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}
    }
    errors = [r for r in caplog.records if r.name == "ezermala.errors"]
    assert len(errors) == 1
    assert "RuntimeError" in errors[0].getMessage()
    assert "/submissions" in errors[0].getMessage()
    for record in caplog.records:
        assert SECRET not in record.getMessage()
        assert record.exc_info is None

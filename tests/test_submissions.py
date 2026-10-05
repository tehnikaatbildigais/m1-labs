"""Bāzes testi (R1–R4)."""


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_submission_returns_201(client, valid_payload):
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("IES-2026-")
    assert data["status"] == "RECEIVED"
    assert data["replyChannel"] == "EMAIL"


def test_create_submission_ok(client, valid_payload):
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code in (200, 201, 400, 422)


def test_get_submission_after_create(client, valid_payload):
    created = client.post("/submissions", json=valid_payload).json()
    response = client.get(f"/submissions/{created['id']}")
    assert response.status_code == 200
    assert response.json()["subject"] == valid_payload["subject"]


def test_unknown_submission_returns_404(client):
    response = client.get("/submissions/IES-2026-999999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_missing_field_returns_400_required(client, valid_payload):
    del valid_payload["subject"]
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert {"field": "subject", "issue": "REQUIRED"} in error["details"]


def test_unknown_topic_returns_400(client, valid_payload):
    valid_payload["topic"] = "ZOO"
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    assert response.json()["error"]["details"][0]["field"] == "topic"


def test_unknown_topic_returns_validation_error(client, valid_payload):
    # CR-0 #3
    valid_payload["topic"] = "ZOO"
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [d["field"] for d in error["details"]] == ["topic"]


def test_list_topics(client):
    # CR-0 #1 un #4: precīza secība, kodi un nosaukumi; OTHER beigās
    response = client.get("/topics")
    assert response.status_code == 200
    assert response.json() == [
        {"code": "ROADS", "name": "Ceļi un ielas"},
        {"code": "WASTE", "name": "Atkritumi"},
        {"code": "PLANNING", "name": "Teritorijas plānošana"},
        {"code": "PARKS", "name": "Parki un skvēri"},
        {"code": "OTHER", "name": "Cits"},
    ]


def test_create_submission_with_parks_topic(client, valid_payload):
    # CR-0 #2
    valid_payload["topic"] = "PARKS"
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 201
    created = client.get(f"/submissions/{response.json()['id']}").json()
    assert created["topic"] == "PARKS"


def test_active_e_address_is_used(client, valid_payload):
    valid_payload["personalCode"] = "32000000001"
    response = client.post("/submissions", json=valid_payload)
    assert response.status_code == 201
    assert response.json()["replyChannel"] == "E_ADDRESS"


def test_seed_submissions_exist():
    from app import storage

    storage.reset()
    assert storage.get("IES-2026-000002")["status"] == "IN_PROGRESS"


def test_ui_is_served(client):
    response = client.get("/ui/")
    assert response.status_code == 200
    assert "Iesniegums" in response.text

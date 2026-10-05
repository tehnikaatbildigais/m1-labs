"""CR-3: iesniegumu saraksts darbiniekam (piegādātāja testi)."""

from app import storage


def test_list_received(client):
    storage.reset()
    response = client.get("/submissions?status=RECEIVED")
    assert response.status_code == 200
    assert all(item["status"] == "RECEIVED" for item in response.json())


def test_list_by_topic(client):
    storage.reset()
    response = client.get("/submissions?topic=ROADS")
    assert response.status_code == 200
    assert all(item["topic"] == "ROADS" for item in response.json())


def test_list_all(client):
    storage.reset()
    response = client.get("/submissions")
    assert response.status_code == 200
    assert len(response.json()) == 3

from fastapi.testclient import TestClient

import lumio.main

LEAD = {
    "first_name": "Ana",
    "last_name": "B",
    "email": "ana@cabinet-exemple.fr",
    "job_title": "DRH",
    "company_name": "Clinique X",
}


def client(monkeypatch, secret):
    monkeypatch.setenv("WEBHOOK_SECRET", secret)
    monkeypatch.setattr(lumio.main, "process_lead", lambda *_: {"verdict": "qualifie"})
    return TestClient(lumio.main.app)


def test_secret_is_required_when_configured(monkeypatch):
    http = client(monkeypatch, "s3cret")
    assert http.post("/webhook/demo-request", json=LEAD).status_code == 401
    headers = {"X-Webhook-Secret": "s3cret"}
    assert http.post("/webhook/demo-request", json=LEAD, headers=headers).status_code == 200


def test_invalid_lead_is_rejected(monkeypatch):
    http = client(monkeypatch, "")
    assert http.post("/webhook/demo-request", json={"email": "x"}).status_code == 422

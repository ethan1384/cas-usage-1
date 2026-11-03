import json

import httpx
import pytest
from fastapi.testclient import TestClient

from lumio import mock_hubspot
from lumio.config import Settings
from lumio.connectors import HUBSPOT_EXISTING, HUBSPOT_SENT_TO_MOCK, deliver
from lumio.models import Decision, Lead, Verdict


@pytest.fixture
def http(monkeypatch):
    monkeypatch.setenv("MOCK_HUBSPOT", "1")
    import importlib

    import lumio.main

    importlib.reload(lumio.main)
    mock_hubspot.reset()
    return TestClient(lumio.main.app, base_url="http://testserver")


def decision(email="ana@cabinet-exemple.fr", verdict=Verdict.QUALIFIED, name="Ana"):
    lead = Lead(first_name=name, last_name="B", email=email, job_title="DRH", company_name="Clinique X")
    return Decision(lead=lead, company=None, verdict=verdict, reasons=["raison"], assignee="Noa")


def settings(tmp_path):
    return Settings(
        data_dir=tmp_path, hubspot_token="demo", hubspot_base_url="http://testserver/mock/hubspot"
    )


def test_second_creation_with_same_email_is_refused_and_keeps_the_first_status(http, tmp_path):
    first = deliver(http, settings(tmp_path), decision(verdict=Verdict.QUALIFIED))
    second = deliver(http, settings(tmp_path), decision(verdict=Verdict.OUT))
    assert first["hubspot"] == HUBSPOT_SENT_TO_MOCK
    assert second["hubspot"] == HUBSPOT_EXISTING
    page = http.get("/mock/hubspot").text
    assert "Contacts reçus : 1" in page
    assert "qualifié" in page and "hors cible" not in page


def test_request_without_token_is_unauthorized(http):
    response = http.post("/mock/hubspot/crm/v3/objects/contacts", json={"properties": {"email": "a@b.fr"}})
    assert response.status_code == 401


def test_page_escapes_contact_data(http, tmp_path):
    deliver(http, settings(tmp_path), decision(email="x@cabinet-exemple.fr", name="<script>alert(1)</script>"))
    page = http.get("/mock/hubspot").text
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_mock_is_not_mounted_by_default(monkeypatch):
    monkeypatch.delenv("MOCK_HUBSPOT", raising=False)
    import importlib

    import lumio.main

    importlib.reload(lumio.main)
    assert TestClient(lumio.main.app).get("/mock/hubspot").status_code == 404


def test_reset_empties_the_contacts_so_the_demo_can_be_replayed(http, tmp_path):
    deliver(http, settings(tmp_path), decision())
    assert http.post("/mock/hubspot/reset").json() == {"status": "ok"}
    again = deliver(http, settings(tmp_path), decision())
    assert again["hubspot"] == HUBSPOT_SENT_TO_MOCK

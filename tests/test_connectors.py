import json

import httpx

from lumio.config import Settings
from lumio.connectors import HUBSPOT_EXISTING, deliver, hubspot_payload, slack_payload
from lumio.models import Decision, Lead, Verdict

SECRET_URL = "https://hooks.slack.com/services/T000/B000/SECRET"


def decision(verdict=Verdict.QUALIFIED, message="Bonjour"):
    lead = Lead(
        first_name="Ana",
        last_name="B",
        email="ana@cabinet-exemple.fr",
        job_title="DRH",
        company_name="Clinique X",
        message=message,
    )
    return Decision(lead=lead, company=None, verdict=verdict, reasons=["raison"], assignee="Noa")


def test_slack_message_cannot_ping_the_channel():
    text = slack_payload(decision(message="<!channel> urgent"))["text"]
    assert "<!channel>" not in text
    assert "&lt;!channel&gt;" in text


def test_hubspot_contact_carries_email_and_status():
    properties = hubspot_payload(decision(Verdict.OUT))["properties"]
    assert properties["email"] == "ana@cabinet-exemple.fr"
    assert properties["hs_lead_status"] == "UNQUALIFIED"


def test_existing_hubspot_contact_is_left_untouched_and_slack_says_so(tmp_path):
    sent = []

    def handler(request):
        sent.append(request)
        if "hubapi.com" in str(request.url):
            return httpx.Response(409, json={"message": "Contact already exists"})
        return httpx.Response(200)

    settings = Settings(data_dir=tmp_path, slack_webhook_url=SECRET_URL, hubspot_token="t")
    statuses = deliver(httpx.Client(transport=httpx.MockTransport(handler)), settings, decision())
    assert statuses == {"hubspot": HUBSPOT_EXISTING, "slack": "envoyé"}
    assert all(request.method == "POST" for request in sent)  # jamais de PATCH ni d'upsert
    slack_body = json.loads(next(r for r in sent if "slack" in str(r.url)).content)
    assert "déjà présent dans HubSpot" in slack_body["text"]


def test_without_credentials_everything_is_simulated(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
    statuses = deliver(client, Settings(data_dir=tmp_path), decision())
    assert statuses == {"hubspot": "simulé", "slack": "simulé"}
    targets = [json.loads(line)["target"] for line in (tmp_path / "outbox.jsonl").open()]
    assert targets == ["hubspot", "slack"]


def test_out_of_target_lead_does_not_notify_slack(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    settings = Settings(data_dir=tmp_path, slack_webhook_url=SECRET_URL, hubspot_token="t")
    assert deliver(client, settings, decision(Verdict.OUT)) == {"hubspot": "envoyé", "slack": "ignoré"}


def test_delivery_error_is_reported_without_leaking_the_slack_url(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403)))
    settings = Settings(data_dir=tmp_path, slack_webhook_url=SECRET_URL, hubspot_token="t")
    statuses = deliver(client, settings, decision())
    assert statuses == {"hubspot": "erreur HTTP 403", "slack": "erreur HTTP 403"}
    assert "SECRET" not in json.dumps(statuses)


def test_dry_run_sends_nothing_even_with_credentials(tmp_path):
    def fail(_):
        raise AssertionError("aucun appel réseau attendu")

    client = httpx.Client(transport=httpx.MockTransport(fail))
    settings = Settings(data_dir=tmp_path, slack_webhook_url=SECRET_URL, hubspot_token="t", dry_run=True)
    assert deliver(client, settings, decision()) == {"hubspot": "simulé", "slack": "simulé"}

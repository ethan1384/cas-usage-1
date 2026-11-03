import json
import logging
from pathlib import Path

import httpx

from lumio.config import HUBSPOT_API, Settings
from lumio.models import Decision, Verdict

logger = logging.getLogger(__name__)

HUBSPOT_CONTACTS_PATH = "/crm/v3/objects/contacts"
HUBSPOT_EXISTING = "déjà existant, non modifié"
HUBSPOT_SENT_TO_MOCK = "envoyé au simulateur local"
LEAD_STATUS = {
    Verdict.QUALIFIED: "NEW",
    Verdict.REVIEW: "OPEN",
    Verdict.OUT: "UNQUALIFIED",
}
SLACK_TITLES = {
    Verdict.QUALIFIED: ":large_green_circle: Lead qualifié",
    Verdict.REVIEW: ":large_yellow_circle: Lead à revoir",
}


def _escape_slack(text: str) -> str:
    """Le formulaire est public : sans ça, un message pourrait déclencher un <!channel>."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hubspot_payload(decision: Decision) -> dict:
    lead = decision.lead
    return {
        "properties": {
            "email": lead.email,
            "firstname": lead.first_name,
            "lastname": lead.last_name,
            "jobtitle": lead.job_title,
            "company": decision.company.name if decision.company else lead.company_name,
            "hs_lead_status": LEAD_STATUS[decision.verdict],
        }
    }


def slack_payload(decision: Decision, existing_contact: bool = False) -> dict:
    lead = decision.lead
    lines = [
        f"*{SLACK_TITLES[decision.verdict]}* : {lead.first_name} {lead.last_name}, "
        f"{lead.job_title} ({decision.company.name if decision.company else lead.company_name})",
    ]
    if decision.assignee:
        lines.append(f"Attribué à : {decision.assignee}")
    if existing_contact:
        lines.append("Contact déjà présent dans HubSpot : fiche et statut laissés tels quels")
    lines += [f"• {reason}" for reason in decision.reasons]
    if lead.message:
        lines.append(f"> {lead.message}")
    return {"text": _escape_slack("\n".join(lines))}


def _record_simulation(data_dir: Path, target: str, payload: dict) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "outbox.jsonl").open("a", encoding="utf-8") as outbox:
        outbox.write(json.dumps({"target": target, "payload": payload}, ensure_ascii=False) + "\n")


def _send(
    client: httpx.Client,
    settings: Settings,
    target: str,
    url: str,
    payload: dict,
    headers: dict | None = None,
    tolerated: dict[int, str] | None = None,
) -> str:
    """Envoie ou simule. Le statut ne reprend jamais l'URL : celle de Slack est un secret."""
    if settings.dry_run or not url:
        _record_simulation(settings.data_dir, target, payload)
        return "simulé"
    try:
        response = client.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if tolerated and status in tolerated:
            return tolerated[status]
        logger.error("%s a répondu %s", target, status)
        return f"erreur HTTP {status}"
    except httpx.HTTPError as exc:
        logger.error("%s injoignable : %s", target, type(exc).__name__)
        return f"erreur {type(exc).__name__}"
    return "envoyé"


def deliver(client: httpx.Client, settings: Settings, decision: Decision) -> dict[str, str]:
    # Création seule : un contact déjà suivi par un commercial n'est jamais écrasé.
    # HubSpot refuse la création d'un e-mail existant (409, à confirmer sur un vrai compte).
    hubspot_url = f"{settings.hubspot_base_url}{HUBSPOT_CONTACTS_PATH}" if settings.hubspot_token else ""
    statuses = {
        "hubspot": _send(
            client,
            settings,
            "hubspot",
            hubspot_url,
            hubspot_payload(decision),
            {"Authorization": f"Bearer {settings.hubspot_token}"},
            tolerated={409: HUBSPOT_EXISTING},
        )
    }
    if statuses["hubspot"] == "envoyé" and settings.hubspot_base_url != HUBSPOT_API:
        statuses["hubspot"] = HUBSPOT_SENT_TO_MOCK
    # Les leads hors cible ne dérangent pas l'équipe : ils restent dans le CRM et le journal.
    if decision.verdict is Verdict.OUT:
        statuses["slack"] = "ignoré"
    else:
        payload = slack_payload(decision, existing_contact=statuses["hubspot"] == HUBSPOT_EXISTING)
        statuses["slack"] = _send(client, settings, "slack", settings.slack_webhook_url, payload)
    return statuses

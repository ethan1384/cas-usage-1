import csv
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx

from lumio.config import Settings
from lumio.connectors import deliver
from lumio.enrichment import find_company
from lumio.llm import LLMError, analyze
from lumio.models import Analysis, Decision, Lead, Verdict
from lumio.routing import build_decision
from lumio.rules import evaluate

logger = logging.getLogger(__name__)

JOURNAL_FIELDS = ["date", "email", "structure", "siren", "verdict", "assignee", "reasons", "hubspot", "slack"]


def qualify(client: httpx.Client, settings: Settings, lead: Lead) -> Decision:
    enrichment = find_company(client, lead)
    rules = evaluate(enrichment.company, enrichment.note)

    analysis: Analysis | None = None
    # Pas d'appel LLM quand les règles suffisent à écarter : moins de coût et de données envoyées.
    if rules.verdict is not Verdict.OUT:
        try:
            analysis = analyze(client, settings, lead)
        except LLMError as exc:
            logger.error("Analyse LLM impossible : %s", exc)

    return build_decision(lead, enrichment.company, rules, analysis)


def _write_journal(data_dir: Path, decision: Decision, statuses: dict[str, str]) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / "decisions.csv"
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as journal:
        writer = csv.DictWriter(journal, fieldnames=JOURNAL_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "date": datetime.now(UTC).isoformat(timespec="seconds"),
                "email": decision.lead.email,
                "structure": decision.lead.company_name,
                "siren": decision.company.siren if decision.company else "",
                "verdict": decision.verdict.value,
                "assignee": decision.assignee or "",
                "reasons": " | ".join(decision.reasons),
                "hubspot": statuses["hubspot"],
                "slack": statuses["slack"],
            }
        )


def process_lead(client: httpx.Client, settings: Settings, lead: Lead) -> dict:
    decision = qualify(client, settings, lead)
    statuses = deliver(client, settings, decision)
    _write_journal(settings.data_dir, decision, statuses)
    return {
        "verdict": decision.verdict.value,
        "assignee": decision.assignee,
        "company": decision.company.model_dump() if decision.company else None,
        "reasons": decision.reasons,
        "delivery": statuses,
    }

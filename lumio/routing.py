import zlib

from lumio.models import Analysis, Company, Decision, Lead, RuleResult, Verdict

SALES_TEAM = ("Camille", "Sacha", "Noa", "Alex")


def assign_sales_rep(email: str) -> str:
    """Sans état : un même contact retombe toujours sur le même commercial."""
    return SALES_TEAM[zlib.crc32(email.lower().encode()) % len(SALES_TEAM)]


def decide(rules: RuleResult, analysis: Analysis | None) -> tuple[Verdict, list[str]]:
    """Combine règles et LLM. Le LLM ne peut jamais repêcher ce que les règles ont écarté."""
    reasons = list(rules.reasons)
    if rules.verdict is Verdict.OUT:
        return Verdict.OUT, reasons
    if analysis is None:
        return Verdict.REVIEW, reasons + ["Analyse IA indisponible"]

    reasons.append(analysis.justification)
    if analysis.red_flag != "aucun":
        reasons.append(f"Signal d'alerte : {analysis.red_flag}")
        confident = analysis.certainty == "elevee"
        return (Verdict.OUT if confident else Verdict.REVIEW), reasons
    if not analysis.is_decision_maker:
        reasons.append("Contact non décideur : remonter vers la direction ou le DRH")

    if rules.verdict is Verdict.REVIEW:
        return Verdict.REVIEW, reasons
    if analysis.certainty == "faible" or analysis.intent == "faible":
        return Verdict.REVIEW, reasons
    return Verdict.QUALIFIED, reasons


def build_decision(
    lead: Lead, company: Company | None, rules: RuleResult, analysis: Analysis | None
) -> Decision:
    verdict, reasons = decide(rules, analysis)
    assignee = assign_sales_rep(lead.email) if verdict is Verdict.QUALIFIED else None
    return Decision(
        lead=lead,
        company=company,
        verdict=verdict,
        reasons=reasons,
        analysis=analysis,
        assignee=assignee,
    )

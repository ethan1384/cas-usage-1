"""Rejoue le jeu de test et compare le tri par règles seules au tri règles + LLM.

Usage : uv run python -m lumio.evaluate
Les appels au registre et au LLM sont réels : compter quelques minutes.
"""

import argparse
import json
import logging
from pathlib import Path

import httpx

from lumio.config import Settings
from lumio.enrichment import find_company
from lumio.llm import LLMError, analyze
from lumio.models import Lead, Verdict
from lumio.routing import decide
from lumio.rules import evaluate

LABELS = [Verdict.QUALIFIED.value, Verdict.REVIEW.value, Verdict.OUT.value]
Q, R, O = LABELS


def metrics(pairs: list[tuple[str, str]]) -> dict:
    """pairs : (réponse attendue, réponse du système)."""
    matrix = {e: {p: 0 for p in LABELS} for e in LABELS}
    for expected, predicted in pairs:
        matrix[expected][predicted] += 1

    def count(condition) -> int:
        return sum(1 for e, p in pairs if condition(e, p))

    return {
        "n": len(pairs),
        "matrix": matrix,
        "accuracy": count(lambda e, p: e == p) / len(pairs),
        "lost_leads": count(lambda e, p: p == O and e != O),
        "false_qualified": count(lambda e, p: p == Q and e != Q),
        "filtered": count(lambda e, p: e == O and p == O),
        "expected_out": count(lambda e, p: e == O),
        "auto_qualified": count(lambda e, p: e == Q and p == Q),
        "expected_qualified": count(lambda e, p: e == Q),
        "review_share": count(lambda e, p: p == R) / len(pairs),
    }


def _pct(part: int, total: int) -> str:
    return f"{part}/{total} ({100 * part / total:.0f} %)" if total else "n/a"


def _matrix_table(matrix: dict) -> list[str]:
    lines = ["| attendu \\ obtenu | " + " | ".join(LABELS) + " |", "|---|" + "---|" * len(LABELS)]
    lines += [f"| **{e}** | " + " | ".join(str(matrix[e][p]) for p in LABELS) + " |" for e in LABELS]
    return lines


def render_report(rows: list[dict], model: str) -> str:
    rules_only = metrics([(r["expected"], r["rules"]) for r in rows])
    full = metrics([(r["expected"], r["full"]) for r in rows])
    lines = [
        "# Évaluation du tri",
        "",
        f"{len(rows)} leads, modèle `{model}`, registre public réel. Réponses attendues fixées avant les "
        "mesures (`data/testset.jsonl`).",
        "",
        "| Indicateur | Règles seules | Règles + LLM |",
        "|---|---|---|",
        f"| Réponse exacte | {_pct(round(rules_only['accuracy'] * len(rows)), len(rows))} "
        f"| {_pct(round(full['accuracy'] * len(rows)), len(rows))} |",
        f"| **Leads perdus** (écartés à tort) | {rules_only['lost_leads']} | {full['lost_leads']} |",
        f"| Faux qualifiés (envoyés à un commercial à tort) | {rules_only['false_qualified']} "
        f"| {full['false_qualified']} |",
        f"| Hors cible écartés automatiquement | {_pct(rules_only['filtered'], rules_only['expected_out'])} "
        f"| {_pct(full['filtered'], full['expected_out'])} |",
        f"| Bons leads qualifiés automatiquement | "
        f"{_pct(rules_only['auto_qualified'], rules_only['expected_qualified'])} "
        f"| {_pct(full['auto_qualified'], full['expected_qualified'])} |",
        f"| Part envoyée en revue humaine | {rules_only['review_share']:.0%} | {full['review_share']:.0%} |",
        "",
        "## Règles + LLM : matrice de confusion",
        "",
        *_matrix_table(full["matrix"]),
        "",
        "## Écarts avec la réponse attendue (règles + LLM)",
        "",
        "| id | catégorie | attendu | règles seules | règles + LLM | première raison utile |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        if row["full"] != row["expected"]:
            lines.append(
                f"| {row['id']} | {row['category']} | {row['expected']} | {row['rules']} "
                f"| {row['full']} | {row['reason'].replace('|', '/')} |"
            )
    return "\n".join(lines) + "\n"


def run_case(client: httpx.Client, settings: Settings, case: dict) -> dict:
    lead = Lead.model_validate(case["lead"])
    enrichment = find_company(client, lead)
    rules = evaluate(enrichment.company, enrichment.note)
    analysis = None
    if rules.verdict is not Verdict.OUT:
        try:
            analysis = analyze(client, settings, lead)
        except LLMError:
            pass
    verdict, reasons = decide(rules, analysis)
    return {
        "id": case["id"],
        "category": case["category"],
        "expected": case["expected"],
        "rules": rules.verdict.value,
        "full": verdict.value,
        "reason": reasons[-1] if reasons else "",
        "company": enrichment.company.name if enrichment.company else None,
        "enrichment_note": enrichment.note,
        "llm_used": analysis is not None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Évalue le tri sur le jeu de test.")
    parser.add_argument("--testset", type=Path, default=Path("data/testset.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("data/eval_report.md"))
    parser.add_argument("--details", type=Path, default=Path("data/eval_details.jsonl"))
    args = parser.parse_args()

    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = Settings.from_env()
    cases = [json.loads(line) for line in args.testset.read_text(encoding="utf-8").splitlines() if line]
    rows = []
    with httpx.Client() as client:
        for number, case in enumerate(cases, 1):
            rows.append(run_case(client, settings, case))
            print(f"[{number}/{len(cases)}] {case['id']} : attendu {rows[-1]['expected']}, "
                  f"obtenu {rows[-1]['full']}", flush=True)

    args.details.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    report = render_report(rows, settings.ollama_model)
    args.report.write_text(report, encoding="utf-8")
    print("\n" + report)


if __name__ == "__main__":
    main()

from lumio.models import Analysis, RuleResult, Verdict
from lumio.routing import SALES_TEAM, assign_sales_rep, decide

PASS = RuleResult(verdict=Verdict.QUALIFIED, reasons=["ok"])
DOUBT = RuleResult(verdict=Verdict.REVIEW, reasons=["doute"])
OUT = RuleResult(verdict=Verdict.OUT, reasons=["non"])


def analysis(**overrides):
    values = {
        "is_decision_maker": True,
        "intent": "forte",
        "red_flag": "aucun",
        "certainty": "elevee",
        "justification": "Besoin concret.",
    }
    return Analysis(**(values | overrides))


def test_llm_cannot_rescue_a_lead_rejected_by_rules():
    assert decide(OUT, analysis())[0] is Verdict.OUT


def test_good_rules_and_good_analysis_qualify():
    assert decide(PASS, analysis())[0] is Verdict.QUALIFIED


def test_llm_failure_never_loses_a_lead():
    verdict, reasons = decide(PASS, None)
    assert verdict is Verdict.REVIEW
    assert "Analyse IA indisponible" in reasons


def test_doubtful_rules_stay_in_review_even_with_good_analysis():
    assert decide(DOUBT, analysis())[0] is Verdict.REVIEW


def test_red_flag_rejects_only_when_certain():
    assert decide(PASS, analysis(red_flag="etudiant"))[0] is Verdict.OUT
    assert decide(PASS, analysis(red_flag="etudiant", certainty="moyenne"))[0] is Verdict.REVIEW


def test_low_intent_or_certainty_goes_to_review():
    assert decide(PASS, analysis(intent="faible"))[0] is Verdict.REVIEW
    assert decide(PASS, analysis(certainty="faible"))[0] is Verdict.REVIEW


def test_non_decision_maker_in_target_stays_qualified_but_flagged():
    verdict, reasons = decide(PASS, analysis(is_decision_maker=False))
    assert verdict is Verdict.QUALIFIED
    assert any("non décideur" in reason for reason in reasons)


def test_assignment_is_stable_and_case_insensitive():
    assert assign_sales_rep("A@b.fr") == assign_sales_rep("a@b.fr")
    assert assign_sales_rep("a@b.fr") in SALES_TEAM


def test_red_flag_contact_is_not_escalated_to_management():
    _, reasons = decide(PASS, analysis(red_flag="etudiant", is_decision_maker=False))
    assert not any("non décideur" in reason for reason in reasons)

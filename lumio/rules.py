from lumio.models import Company, RuleResult, Verdict
from lumio.text import normalize

# Cliniques, médecins, spécialistes, dentaires, laboratoires d'analyses.
TARGET_NAF = {"86.10Z", "86.21Z", "86.22A", "86.22B", "86.22C", "86.23Z", "86.90B"}
# 20-49, 50-99, 100-199, 200-249, 250-499 salariés (codes INSEE).
TARGET_HEADCOUNT = {"12", "21", "22", "31", "32"}
# Hébergement médico-social (EHPAD...) et action sociale : même besoin de planning de soignants,
# mais hors de la liste de cibles, donc une personne tranche au lieu d'écarter sans preuve.
ADJACENT_NAF_PREFIXES = ("87", "88")
VETERINARY_NAF = "75.00Z"
# Des centres de santé sont gérés par des mutuelles ou des associations, donc hors NAF 86.
HEALTH_NAME_HINTS = ("clinique", "dentaire", "sante", "medical", "laboratoire", "hopital")


def _check_sector(company: Company) -> tuple[Verdict, str]:
    naf = company.naf
    if naf in TARGET_NAF:
        return Verdict.QUALIFIED, f"Secteur dans la cible (NAF {naf})"
    if naf and naf.startswith("86"):
        return Verdict.REVIEW, f"Secteur santé hors liste principale (NAF {naf})"
    if naf and naf.startswith(ADJACENT_NAF_PREFIXES):
        return Verdict.REVIEW, f"Secteur médico-social voisin de la cible (NAF {naf})"
    if naf == VETERINARY_NAF or "veterinaire" in normalize(company.name):
        return Verdict.OUT, "Secteur vétérinaire hors cible"
    if any(hint in normalize(company.name) for hint in HEALTH_NAME_HINTS):
        return Verdict.REVIEW, f"Nom lié à la santé mais NAF {naf or 'inconnu'}"
    return Verdict.OUT, f"Secteur hors cible (NAF {naf or 'inconnu'})"


def _check_headcount(company: Company) -> tuple[Verdict, str]:
    band = company.headcount_band
    if band in TARGET_HEADCOUNT:
        return Verdict.QUALIFIED, f"Effectif dans la cible (tranche INSEE {band})"
    if band in (None, "NN"):
        return Verdict.REVIEW, "Effectif non renseigné dans le registre"
    return Verdict.OUT, f"Effectif hors cible (tranche INSEE {band})"


def evaluate(company: Company | None, note: str | None = None) -> RuleResult:
    """Applique les critères objectifs. Écarter exige une preuve : le doute part en revue."""
    if company is None:
        return RuleResult(verdict=Verdict.REVIEW, reasons=[note or "Structure non vérifiée"])
    checks = [_check_sector(company), _check_headcount(company)]
    verdicts = {verdict for verdict, _ in checks}
    if Verdict.OUT in verdicts:
        verdict = Verdict.OUT
    elif Verdict.REVIEW in verdicts:
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.QUALIFIED
    return RuleResult(verdict=verdict, reasons=[reason for _, reason in checks])

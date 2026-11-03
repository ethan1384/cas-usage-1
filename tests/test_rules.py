from lumio.models import Company, Verdict
from lumio.rules import evaluate


def company(naf="86.23Z", band="12", name="Centre dentaire du Parc"):
    return Company(siren="123456789", name=name, naf=naf, headcount_band=band, city="Paris")


def test_target_sector_and_size_pass():
    assert evaluate(company()).verdict is Verdict.QUALIFIED


def test_boundaries_of_target_size():
    assert evaluate(company(band="11")).verdict is Verdict.OUT  # 10-19 salariés
    assert evaluate(company(band="12")).verdict is Verdict.QUALIFIED  # 20-49
    assert evaluate(company(band="32")).verdict is Verdict.QUALIFIED  # 250-499
    assert evaluate(company(band="41")).verdict is Verdict.OUT  # 500-999


def test_unknown_headcount_goes_to_review_not_out():
    assert evaluate(company(band="NN")).verdict is Verdict.REVIEW
    assert evaluate(company(band=None)).verdict is Verdict.REVIEW


def test_unrelated_sector_is_out():
    assert evaluate(company(naf="62.02A", name="Capgemini")).verdict is Verdict.OUT


def test_health_center_with_non_health_naf_goes_to_review():
    result = evaluate(company(naf="94.99Z", name="Association centre de santé des Lilas"))
    assert result.verdict is Verdict.REVIEW


def test_oversized_health_structure_is_out_even_with_good_sector():
    assert evaluate(company(band="51")).verdict is Verdict.OUT


def test_missing_company_goes_to_review_with_note():
    result = evaluate(None, "Structure introuvable dans le registre")
    assert result.verdict is Verdict.REVIEW
    assert result.reasons == ["Structure introuvable dans le registre"]


def test_veterinary_clinic_is_out_despite_health_looking_name():
    result = evaluate(company(naf="75.00Z", name="CLINIQUE VETERINAIRE DES FALUNS"))
    assert result.verdict is Verdict.OUT


def test_nursing_home_goes_to_review_not_out():
    result = evaluate(company(naf="87.10A", band="21", name="EHPAD RESIDENCE DU PARC"))
    assert result.verdict is Verdict.REVIEW


def test_nursing_home_of_wrong_size_is_still_out():
    assert evaluate(company(naf="87.10A", band="11", name="EHPAD RESIDENCE DU PARC")).verdict is Verdict.OUT

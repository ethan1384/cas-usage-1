import httpx

from lumio.enrichment import find_company
from lumio.models import Lead


def lead(company_name="Centre dentaire du Parc"):
    return Lead(
        first_name="A",
        last_name="B",
        email="a@cabinet-exemple.fr",
        job_title="Directrice",
        company_name=company_name,
    )


def result(name, siren="111111111"):
    return {
        "siren": siren,
        "nom_complet": name,
        "nom_raison_sociale": name,
        "activite_principale": "86.23Z",
        "tranche_effectif_salarie": "12",
        "siege": {"libelle_commune": "PARIS"},
    }


def client_returning(results, status=200):
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json={"results": results}))
    return httpx.Client(transport=transport)


def test_single_match_is_kept():
    enrichment = find_company(client_returning([result("CENTRE DENTAIRE DU PARC")]), lead())
    assert enrichment.company.siren == "111111111"


def test_unrelated_result_is_not_accepted():
    enrichment = find_company(client_returning([result("BOULANGERIE DU PARC")]), lead())
    assert enrichment.company is None
    assert "introuvable" in enrichment.note


def test_homonyms_without_exact_match_are_not_guessed():
    results = [
        result("CENTRE DENTAIRE DU PARC LYON", "111111111"),
        result("CENTRE DENTAIRE DU PARC NICE", "222222222"),
    ]
    enrichment = find_company(client_returning(results), lead())
    assert enrichment.company is None
    assert "homonymes" in enrichment.note


def test_exact_name_wins_over_partial_matches():
    results = [
        result("CENTRE DENTAIRE DU PARC NICE", "222222222"),
        result("Centre dentaire du Parc", "333333333"),
    ]
    assert find_company(client_returning(results), lead()).company.siren == "333333333"


def test_api_failure_returns_a_note_instead_of_crashing():
    enrichment = find_company(client_returning([], status=500), lead())
    assert enrichment.company is None
    assert "indisponible" in enrichment.note


def test_transient_registry_errors_are_retried(monkeypatch):
    monkeypatch.setattr("lumio.enrichment.time.sleep", lambda _: None)
    answers = iter([httpx.Response(429), httpx.Response(503), httpx.Response(200, json={"results": [result("CENTRE DENTAIRE DU PARC")]})])
    client = httpx.Client(transport=httpx.MockTransport(lambda _: next(answers)))
    assert find_company(client, lead()).company.siren == "111111111"


def test_client_errors_are_not_retried(monkeypatch):
    monkeypatch.setattr("lumio.enrichment.time.sleep", lambda _: None)
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(400)))
    assert "indisponible" in find_company(client, lead()).note
    assert len(calls) == 1


def test_persistent_failure_gives_up_after_three_attempts(monkeypatch):
    monkeypatch.setattr("lumio.enrichment.time.sleep", lambda _: None)
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(429)))
    assert "indisponible" in find_company(client, lead()).note
    assert len(calls) == 3

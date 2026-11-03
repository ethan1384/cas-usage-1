import time

import httpx

from lumio.models import Company, Enrichment, Lead
from lumio.text import significant_tokens

API_URL = "https://recherche-entreprises.api.gouv.fr/search"
MIN_NAME_OVERLAP = 0.8
ATTEMPTS = 3


def _matches(name: str, result: dict) -> bool:
    wanted = significant_tokens(name)
    if not wanted:
        return False
    found = significant_tokens(result.get("nom_complet") or "")
    return len(wanted & found) / len(wanted) >= MIN_NAME_OVERLAP


def _to_company(result: dict) -> Company:
    return Company(
        siren=result["siren"],
        name=result.get("nom_complet") or result.get("nom_raison_sociale") or "",
        naf=result.get("activite_principale"),
        headcount_band=result.get("tranche_effectif_salarie"),
        city=(result.get("siege") or {}).get("libelle_commune"),
    )


def _search(client: httpx.Client, params: dict) -> list[dict]:
    """Le registre limite le débit : on retente les erreurs passagères avant d'abandonner."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = client.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            return response.json()["results"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429 and exc.response.status_code < 500:
                raise
            if attempt == ATTEMPTS:
                raise
        except httpx.TransportError:
            if attempt == ATTEMPTS:
                raise
        time.sleep(attempt)
    raise AssertionError("inatteignable")


def find_company(client: httpx.Client, lead: Lead) -> Enrichment:
    """Cherche la structure du lead. Dans le doute, n'en retient aucune plutôt qu'un homonyme."""
    params = {"q": lead.company_name, "etat_administratif": "A", "per_page": 10}
    if lead.postal_code:
        params["code_postal"] = lead.postal_code
    try:
        results = _search(client, params)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        return Enrichment(note=f"Registre indisponible ({type(exc).__name__})")

    matches = [r for r in results if _matches(lead.company_name, r)]
    if not matches:
        return Enrichment(note="Structure introuvable dans le registre")

    wanted = significant_tokens(lead.company_name)
    exact = [r for r in matches if significant_tokens(r.get("nom_raison_sociale") or "") == wanted]
    if len(exact) == 1:
        return Enrichment(company=_to_company(exact[0]))
    if len(matches) == 1:
        return Enrichment(company=_to_company(matches[0]))
    return Enrichment(note=f"{len(matches)} structures homonymes dans le registre")

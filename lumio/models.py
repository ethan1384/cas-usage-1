from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class Verdict(StrEnum):
    QUALIFIED = "qualifie"
    REVIEW = "a_revoir"
    OUT = "hors_cible"


class Lead(BaseModel):
    """Une demande de démo telle que reçue du formulaire du site."""

    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: EmailStr
    job_title: str = Field(max_length=150)
    company_name: str = Field(min_length=2, max_length=200)
    postal_code: str | None = Field(default=None, pattern=r"^\d{5}$")
    message: str = Field(default="", max_length=2000)


class Company(BaseModel):
    """Une structure vérifiée dans le registre public."""

    siren: str
    name: str
    naf: str | None
    headcount_band: str | None
    city: str | None


class Enrichment(BaseModel):
    company: Company | None = None
    note: str | None = None


class RuleResult(BaseModel):
    verdict: Verdict
    reasons: list[str]


class Analysis(BaseModel):
    """Sortie du LLM. Ce schéma est aussi celui imposé au modèle."""

    is_decision_maker: bool = Field(
        description="Le poste correspond à direction, DRH ou responsable des opérations."
    )
    intent: Literal["forte", "moyenne", "faible"] = Field(
        description="Besoin réel de planifier des équipes, d'après le message."
    )
    red_flag: Literal["aucun", "etudiant", "concurrent", "recruteur", "prestataire", "spam"]
    certainty: Literal["elevee", "moyenne", "faible"] = Field(
        description="Ta certitude sur cette analyse, pas la probabilité d'achat."
    )
    justification: str = Field(description="Deux phrases au maximum, en français.")


class Decision(BaseModel):
    lead: Lead
    company: Company | None
    verdict: Verdict
    reasons: list[str]
    analysis: Analysis | None = None
    assignee: str | None = None

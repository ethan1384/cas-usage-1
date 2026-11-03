"""Simulateur local de la création de contact HubSpot, pour la démo.

Ce n'est pas HubSpot. Il reproduit seulement ce que Lumio utilise : la création d'un contact par
POST /crm/v3/objects/contacts, avec refus d'un e-mail déjà existant (409, c'est l'hypothèse de Lumio), et
il affiche les contacts reçus dans une page. Activé par MOCK_HUBSPOT=1, jamais en production.
"""

import threading
from datetime import datetime
from html import escape
from itertools import count

from fastapi import APIRouter, Header
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(prefix="/mock/hubspot")

_lock = threading.Lock()
_contacts: list[dict] = []
_ids = count(1)

STATUS_LABELS = {"NEW": "qualifié", "OPEN": "à revoir", "UNQUALIFIED": "hors cible"}
STATUS_COLORS = {"NEW": "#1a7f4b", "OPEN": "#b7791f", "UNQUALIFIED": "#6b7280"}


def reset() -> None:
    with _lock:
        _contacts.clear()


@router.post("/crm/v3/objects/contacts")
def create_contact(body: dict, authorization: str = Header(default="")) -> JSONResponse:
    if not authorization.startswith("Bearer ") or len(authorization) <= len("Bearer "):
        return JSONResponse({"status": "error", "message": "Jeton manquant"}, status_code=401)
    properties = {key: str(value) for key, value in (body.get("properties") or {}).items()}
    email = properties.get("email", "").strip().lower()
    if not email:
        return JSONResponse({"status": "error", "message": "email manquant"}, status_code=400)

    with _lock:
        existing = next((c for c in _contacts if c["properties"]["email"].strip().lower() == email), None)
        if existing:
            message = f"Contact already exists. Existing ID: {existing['id']}"
            return JSONResponse({"status": "error", "category": "CONFLICT", "message": message}, status_code=409)
        contact = {
            "id": str(next(_ids)),
            "properties": properties,
            "createdAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        _contacts.append(contact)
    return JSONResponse(contact, status_code=201)


@router.post("/reset")
def reset_contacts() -> dict:
    """Vide les contacts reçus, pour rejouer une démo sans redémarrer le serveur."""
    reset()
    return {"status": "ok"}


def render_page(contacts: list[dict]) -> str:
    rows = []
    for contact in reversed(contacts):  # les plus récents en haut
        p = contact["properties"]
        status = p.get("hs_lead_status", "")
        badge = (
            f'<span class="badge" style="background:{STATUS_COLORS.get(status, "#6b7280")}">'
            f"{escape(STATUS_LABELS.get(status, status))}</span> <small>{escape(status)}</small>"
        )
        name = f"{p.get('firstname', '')} {p.get('lastname', '')}".strip()
        rows.append(
            f"<tr><td>{escape(name)}</td><td>{escape(p.get('email', ''))}</td>"
            f"<td>{escape(p.get('jobtitle', ''))}</td><td>{escape(p.get('company', ''))}</td>"
            f"<td>{badge}</td><td>{escape(contact['createdAt'][11:19])}</td></tr>"
        )
    body = "".join(rows) or '<tr><td colspan="6" class="empty">Aucun contact reçu pour l\'instant.</td></tr>'
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta http-equiv="refresh" content="2">
<title>Contacts reçus (simulateur CRM)</title>
<style>
body{{font:15px system-ui,sans-serif;margin:32px;color:#1f2937}}
h1{{font-size:20px;margin:0 0 4px}} .note{{color:#6b7280;margin:0 0 20px}}
table{{border-collapse:collapse;width:100%}} th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280}}
.badge{{color:#fff;border-radius:999px;padding:2px 10px;font-size:13px}} small{{color:#9ca3af}}
.empty{{color:#9ca3af;text-align:center;padding:40px}}
</style></head><body>
<h1>Contacts reçus : {len(contacts)}</h1>
<p class="note">Simulateur local, ce n'est pas HubSpot. Il reçoit la même requête de création de contact
que l'API HubSpot et refuse un e-mail déjà existant (hypothèse non vérifiée sur un vrai compte).</p>
<table><thead><tr><th>Nom</th><th>E-mail</th><th>Poste</th><th>Structure</th><th>Statut du lead</th><th>Reçu à</th></tr></thead>
<tbody>{body}</tbody></table></body></html>"""


@router.get("", response_class=HTMLResponse)
def contacts_page() -> str:
    with _lock:
        snapshot = list(_contacts)
    return render_page(snapshot)

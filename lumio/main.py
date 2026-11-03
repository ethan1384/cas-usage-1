import hmac
import logging
import os

import httpx
from fastapi import FastAPI, Header, HTTPException

from lumio.config import Settings
from lumio.models import Lead
from lumio.pipeline import process_lead

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Lumio - qualification des leads")

if os.getenv("MOCK_HUBSPOT"):  # démo uniquement : voir lumio/mock_hubspot.py
    from lumio.mock_hubspot import router as mock_hubspot_router

    app.include_router(mock_hubspot_router)


@app.post("/webhook/demo-request")
def demo_request(lead: Lead, x_webhook_secret: str = Header(default="")) -> dict:
    settings = Settings.from_env()
    if settings.webhook_secret and not hmac.compare_digest(x_webhook_secret, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Secret invalide")
    with httpx.Client() as client:
        return process_lead(client, settings, lead)

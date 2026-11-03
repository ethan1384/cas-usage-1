import argparse
import json
import logging
from pathlib import Path

import httpx

from lumio.config import Settings
from lumio.models import Lead
from lumio.pipeline import process_lead


def main() -> None:
    parser = argparse.ArgumentParser(description="Qualifie un lead depuis un fichier JSON.")
    parser.add_argument("lead_file", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="N'envoie rien à HubSpot ni à Slack")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    lead = Lead.model_validate_json(args.lead_file.read_text(encoding="utf-8"))
    with httpx.Client() as client:
        result = process_lead(client, Settings.from_env(dry_run=args.dry_run), lead)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

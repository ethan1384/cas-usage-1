import os
from dataclasses import dataclass
from pathlib import Path


HUBSPOT_API = "https://api.hubapi.com"


@dataclass(frozen=True)
class Settings:
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gemma4:12b"
    slack_webhook_url: str = ""
    hubspot_token: str = ""
    hubspot_base_url: str = HUBSPOT_API
    webhook_secret: str = ""
    data_dir: Path = Path("data")
    dry_run: bool = False

    @classmethod
    def from_env(cls, dry_run: bool = False) -> "Settings":
        return cls(
            ollama_url=os.getenv("OLLAMA_URL") or cls.ollama_url,
            ollama_model=os.getenv("OLLAMA_MODEL") or cls.ollama_model,
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            hubspot_token=os.getenv("HUBSPOT_TOKEN", ""),
            hubspot_base_url=os.getenv("HUBSPOT_BASE_URL") or HUBSPOT_API,
            webhook_secret=os.getenv("WEBHOOK_SECRET", ""),
            dry_run=dry_run,
        )

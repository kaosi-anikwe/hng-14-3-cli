import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, SecretStr

CREDENTIALS_PATH = Path.home() / ".insighta" / "credentials.json"


class Credentials(BaseModel):
    username: str
    access_token: SecretStr
    refresh_token: SecretStr

    @classmethod
    def load(cls) -> Optional[Credentials]:
        """Load credentials from ~/.insighta/credentials.json."""
        if not CREDENTIALS_PATH.exists():
            return None
        data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        return cls(**data)

    def save(self) -> None:
        """Persist credentials to ~/.insighta/credentials.json."""
        CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS_PATH.write_text(
            json.dumps(
                {
                    "username": self.username,
                    "access_token": self.access_token.get_secret_value(),
                    "refresh_token": self.refresh_token.get_secret_value(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        # Restrict file permissions to owner-only (no-op on Windows)
        try:
            CREDENTIALS_PATH.chmod(0o600)
        except NotImplementedError:
            pass

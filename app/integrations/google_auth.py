import base64
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


BASE_DIR = Path(__file__).resolve().parent.parent.parent

TOKEN_FILE = BASE_DIR / "credentials" / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar",
]


def get_google_credentials() -> Credentials:
    google_token_b64 = os.getenv("GOOGLE_TOKEN_B64")

    if google_token_b64:
        token_json = base64.b64decode(
            google_token_b64
        ).decode("utf-8")

        token_info = json.loads(token_json)

        credentials = Credentials.from_authorized_user_info(
            token_info,
            scopes=SCOPES,
        )

    else:
        if not TOKEN_FILE.exists():
            raise FileNotFoundError(
                f"No se encontró el token de Google en {TOKEN_FILE}"
            )

        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            scopes=SCOPES,
        )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        if not google_token_b64:
            TOKEN_FILE.write_text(
                credentials.to_json(),
                encoding="utf-8",
            )

    if not credentials.valid:
        raise RuntimeError(
            "Las credenciales de Google no son válidas."
        )

    return credentials
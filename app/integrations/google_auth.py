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

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    if not credentials.valid:
        raise RuntimeError(
            "Las credenciales de Google no son válidas."
        )

    return credentials
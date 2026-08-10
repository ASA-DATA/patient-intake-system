from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


BASE_DIR = Path(__file__).resolve().parent.parent

CLIENT_FILE = (
    BASE_DIR
    / "credentials"
    / "google-oauth-client.json"
)

TOKEN_FILE = (
    BASE_DIR
    / "credentials"
    / "token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar",
]

def main() -> None:
    if not CLIENT_FILE.exists():
        raise FileNotFoundError(
            "No se encontró el archivo OAuth en: "
            f"{CLIENT_FILE}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_FILE),
        scopes=SCOPES,
    )

    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        open_browser=True,
        authorization_prompt_message=(
            "Se abrirá el navegador para autorizar Google Drive."
        ),
        success_message=(
            "Autorización completada. "
            "Puedes cerrar esta ventana."
        ),
    )

    TOKEN_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    print("Autorización completada.")
    print(f"Token guardado en: {TOKEN_FILE}")


if __name__ == "__main__":
    main()
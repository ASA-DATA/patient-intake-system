from pprint import pprint

from app.integrations.google_drive import (
    get_drive_information,
)


def main() -> None:
    information = get_drive_information()

    print("Conexión con Google Drive exitosa.")
    pprint(information)


if __name__ == "__main__":
    main()
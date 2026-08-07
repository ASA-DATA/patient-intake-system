from pprint import pprint

from app.services.agenda_excel_service import (
    ensure_agenda_exists,
)


def main() -> None:
    result = ensure_agenda_exists()

    print("Resultado de agenda.xlsx:")
    pprint(result)


if __name__ == "__main__":
    main()
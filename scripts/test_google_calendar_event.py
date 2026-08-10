from datetime import datetime
from zoneinfo import ZoneInfo
from pprint import pprint

from app.integrations.google_calendar import (
    create_calendar_event,
)


def main() -> None:
    timezone = ZoneInfo("America/Mexico_City")

    starts_at = datetime(
        2026,
        8,
        10,
        10,
        0,
        tzinfo=timezone,
    )

    ends_at = datetime(
        2026,
        8,
        10,
        11,
        0,
        tzinfo=timezone,
    )

    result = create_calendar_event(
        summary="Prueba Patient Intake System",
        description=(
            "Evento de prueba creado desde FastAPI."
        ),
        starts_at=starts_at,
        ends_at=ends_at,
    )

    pprint(result)


if __name__ == "__main__":
    main()
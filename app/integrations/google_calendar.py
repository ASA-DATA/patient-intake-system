from datetime import datetime
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from app.core.config import settings

from app.integrations.google_auth import (
    get_google_credentials,
)


def get_calendar_service():
    credentials = get_google_credentials()

    return build(
        "calendar",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

def list_calendars():
    service = get_calendar_service()

    calendars = (
        service.calendarList()
        .list()
        .execute()
    )

    return calendars

def _event_time(value: datetime) -> dict[str, str]:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La fecha del evento debe incluir zona horaria.")
    return {
        "dateTime": value.astimezone(ZoneInfo(settings.clinic_timezone)).isoformat(),
        "timeZone": settings.clinic_timezone,
    }


def create_calendar_event(
    summary: str,
    description: str,
    starts_at: datetime,
    ends_at: datetime,
) -> dict:
    event = {
        "summary": summary,
        "description": description,
        "start": _event_time(starts_at),
        "end": _event_time(ends_at),
    }
    service = get_calendar_service()

    created_event = (
        service.events()
        .insert(
            calendarId="primary",
            body=event,
        )
        .execute()
    )

    return {
        "event_id": created_event["id"],
        "html_link": created_event.get("htmlLink", ""),
        "status": created_event.get("status", ""),
    }

def update_calendar_event(
    event_id: str,
    starts_at: datetime,
    ends_at: datetime,
) -> dict:
    start = _event_time(starts_at)
    end = _event_time(ends_at)
    service = get_calendar_service()

    # Recuperamos primero el evento completo.
    event = (
        service.events()
        .get(
            calendarId="primary",
            eventId=event_id,
        )
        .execute()
    )

    event["start"] = start
    event["end"] = end

    updated_event = (
        service.events()
        .update(
            calendarId="primary",
            eventId=event_id,
            body=event,
        )
        .execute()
    )

    return {
        "event_id": updated_event["id"],
        "html_link": updated_event.get(
            "htmlLink",
            "",
        ),
        "status": updated_event.get(
            "status",
            "",
        ),
    }


def delete_calendar_event(
    event_id: str,
) -> None:
    service = get_calendar_service()

    (
        service.events()
        .delete(
            calendarId="primary",
            eventId=event_id,
        )
        .execute()
    )

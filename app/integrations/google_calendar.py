from googleapiclient.discovery import build

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

def create_calendar_event(
    summary: str,
    description: str,
    starts_at,
    ends_at,
) -> dict:
    service = get_calendar_service()

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": starts_at.isoformat(),
            "timeZone": "America/Mexico_City",
        },
        "end": {
            "dateTime": ends_at.isoformat(),
            "timeZone": "America/Mexico_City",
        },
    }

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
    starts_at,
    ends_at,
) -> dict:
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

    event["start"] = {
        "dateTime": starts_at.isoformat(),
        "timeZone": "America/Mexico_City",
    }

    event["end"] = {
        "dateTime": ends_at.isoformat(),
        "timeZone": "America/Mexico_City",
    }

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
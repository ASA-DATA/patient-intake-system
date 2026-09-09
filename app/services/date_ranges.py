from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


def clinic_date_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """Inclusive clinic dates as an aware, half-open datetime interval."""
    clinic_timezone = ZoneInfo(settings.clinic_timezone)
    return (
        datetime.combine(start_date, time.min, tzinfo=clinic_timezone),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=clinic_timezone),
    )

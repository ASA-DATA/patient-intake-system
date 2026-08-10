from pprint import pprint

from app.integrations.google_calendar import (
    list_calendars,
)

pprint(list_calendars())
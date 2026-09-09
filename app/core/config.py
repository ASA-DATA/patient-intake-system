from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Patient Intake API"
    app_env: str = "development"
    debug: bool = False

    database_url: str
    frontend_url: str = "http://localhost:5173"
    professional_frontend_url: str = "http://localhost:5174"
    PROFESSIONAL_FRONTEND_URL: str="https://nice-tree-012345678.azurestaticapps.net"

    
    clinic_timezone: str = "America/Mexico_City"

    @field_validator("clinic_timezone")
    @classmethod
    def validate_clinic_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("CLINIC_TIMEZONE debe ser una zona horaria IANA válida.") from exc
        return value

    appointment_duration_minutes: int = 60
    opening_hour: int = 7
    closing_hour: int = 20
    availability_days: int = 7

    google_drive_folder_id: str | None = None
    google_calendar_id: str | None = None
    google_service_account_file: str | None = None
    google_drive_expedientes_folder_id: str | None = None
    google_drive_agenda_folder_id: str | None = None

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str | None = None
    twilio_whatsapp_clinic: str | None = None
   
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


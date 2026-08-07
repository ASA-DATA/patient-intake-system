from typing import Any

from googleapiclient.discovery import build

from app.integrations.google_auth import (
    get_google_credentials,
)

from io import BytesIO

from googleapiclient.http import MediaIoBaseUpload

from app.core.config import settings


EXCEL_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)


def upload_excel(
    excel_bytes: bytes,
    filename: str,
) -> dict[str, str]:
    folder_id = settings.google_drive_expedientes_folder_id

    if not folder_id:
        raise RuntimeError(
            "Falta GOOGLE_DRIVE_EXPEDIENTES_FOLDER_ID en .env"
        )

    credentials = get_google_credentials()

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaIoBaseUpload(
        BytesIO(excel_bytes),
        mimetype=EXCEL_MIME_TYPE,
        resumable=False,
    )

    created_file = (
        drive_service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink",
        )
        .execute()
    )

    return {
        "file_id": created_file["id"],
        "name": created_file["name"],
        "web_view_link": created_file.get("webViewLink", ""),
    }


def get_drive_information() -> dict[str, Any]:
    credentials = get_google_credentials()

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    result = (
        drive_service.about()
        .get(
            fields=(
                "user(displayName,emailAddress),"
                "storageQuota(limit,usage)"
            )
        )
        .execute()
    )

    return result
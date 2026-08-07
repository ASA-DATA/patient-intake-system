from typing import Any

from googleapiclient.discovery import build

from app.integrations.google_auth import (
    get_google_credentials,
)

from io import BytesIO

from googleapiclient.http import (MediaIoBaseDownload,MediaIoBaseUpload)

from app.core.config import settings


EXCEL_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)

def upload_excel(
    excel_bytes: bytes,
    filename: str,
    folder_id: str | None = None,
) -> dict[str, str]:
    target_folder_id = (
        folder_id
        or settings.google_drive_expedientes_folder_id
    )

    if not target_folder_id:
        raise RuntimeError(
            "No se configuró una carpeta destino de Google Drive."
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
        "parents": [target_folder_id],
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
        "web_view_link": created_file.get(
            "webViewLink",
            "",
        ),
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

def find_file_in_folder(
    filename: str,
    folder_id: str,
) -> dict[str, str] | None:
    credentials = get_google_credentials()

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    safe_filename = filename.replace("'", "\\'")

    query = (
        f"name = '{safe_filename}' "
        f"and '{folder_id}' in parents "
        "and trashed = false"
    )

    result = (
        drive_service.files()
        .list(
            q=query,
            fields="files(id,name,webViewLink)",
            pageSize=1,
        )
        .execute()
    )

    files = result.get("files", [])

    if not files:
        return None

    return files[0]

def download_file(file_id: str) -> bytes:
    credentials = get_google_credentials()

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    request = drive_service.files().get_media(
        fileId=file_id
    )

    output = BytesIO()

    downloader = MediaIoBaseDownload(
        output,
        request,
    )

    done = False

    while not done:
        _, done = downloader.next_chunk()

    output.seek(0)

    return output.getvalue()

def update_excel_file(
    file_id: str,
    excel_bytes: bytes,
) -> dict[str, str]:
    credentials = get_google_credentials()

    drive_service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )

    media = MediaIoBaseUpload(
        BytesIO(excel_bytes),
        mimetype=EXCEL_MIME_TYPE,
        resumable=False,
    )

    updated_file = (
        drive_service.files()
        .update(
            fileId=file_id,
            media_body=media,
            fields="id,name,webViewLink",
        )
        .execute()
    )

    return {
        "file_id": updated_file["id"],
        "name": updated_file["name"],
        "web_view_link": updated_file.get(
            "webViewLink",
            "",
        ),
    }
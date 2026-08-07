from io import BytesIO
from pprint import pprint

from openpyxl import Workbook

from app.integrations.google_drive import upload_excel


def create_test_excel() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Prueba"

    sheet["A1"] = "Prueba Google Drive"
    sheet["A2"] = "La integración funciona correctamente."

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return output.getvalue()


def main() -> None:
    excel_bytes = create_test_excel()

    result = upload_excel(
        excel_bytes=excel_bytes,
        filename="prueba_google_drive.xlsx",
    )

    print("Archivo subido correctamente.")
    pprint(result)


if __name__ == "__main__":
    main()
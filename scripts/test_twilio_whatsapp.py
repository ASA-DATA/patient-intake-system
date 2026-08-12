from pprint import pprint

from app.core.config import settings
from app.integrations.twilio_whatsapp import (
    send_whatsapp_message,
)


def main() -> None:
    if not settings.twilio_whatsapp_clinic:
        raise RuntimeError(
            "Falta TWILIO_WHATSAPP_CLINIC."
        )

    result = send_whatsapp_message(
        to=settings.twilio_whatsapp_clinic,
        body=(
            "Prueba Patient Intake System.\n\n"
            "La integración con Twilio WhatsApp funciona."
        ),
    )

    pprint(result)


if __name__ == "__main__":
    main()
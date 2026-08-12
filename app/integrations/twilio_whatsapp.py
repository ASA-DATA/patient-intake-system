from twilio.rest import Client

from app.core.config import settings


def get_twilio_client() -> Client:
    if not settings.twilio_account_sid:
        raise RuntimeError(
            "Falta TWILIO_ACCOUNT_SID."
        )

    if not settings.twilio_auth_token:
        raise RuntimeError(
            "Falta TWILIO_AUTH_TOKEN."
        )

    return Client(
        settings.twilio_account_sid,
        settings.twilio_auth_token,
    )


def send_whatsapp_message(
    to: str,
    body: str,
) -> dict[str, str]:
    if not settings.twilio_whatsapp_from:
        raise RuntimeError(
            "Falta TWILIO_WHATSAPP_FROM."
        )

    client = get_twilio_client()

    message = client.messages.create(
        from_=settings.twilio_whatsapp_from,
        to=to,
        body=body,
    )

    return {
        "message_sid": message.sid,
        "status": message.status,
    }
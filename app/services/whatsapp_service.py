import logging
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.integrations.twilio_whatsapp import (
    send_whatsapp_message,
)
from app.models.appointment import Appointment
from app.models.patient import Patient


logger = logging.getLogger(__name__)


def notify_clinic_new_appointment(
    appointment: Appointment,
    patient: Patient,
) -> dict[str, str] | None:
    if not settings.twilio_whatsapp_clinic:
        logger.error(
            "TWILIO_WHATSAPP_CLINIC no está configurado."
        )
        return None

    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    message_body = (
        "Nueva cita registrada\n\n"
        f"Paciente: {patient.full_name}\n"
        f"Teléfono: {patient.phone}\n"
        f"Fecha: {local_start.strftime('%d/%m/%Y')}\n"
        f"Hora: {local_start.strftime('%H:%M')}\n"
        f"Estado: {appointment.status.value}"
    )

    try:
        return send_whatsapp_message(
            to=settings.twilio_whatsapp_clinic,
            body=message_body,
        )

    except Exception:
        logger.exception(
            "No fue posible enviar WhatsApp al consultorio "
            "para la cita %s.",
            appointment.id,
        )

        return None

def notify_patient_new_appointment(
    appointment: Appointment,
    patient: Patient,
    whatsapp_consent: bool,
) -> dict[str, str] | None:
    if not whatsapp_consent:
        logger.info(
            "El paciente %s no autorizó WhatsApp.",
            patient.id,
        )
        return None

    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    patient_whatsapp = f"whatsapp:{patient.phone}"

    message_body = (
        f"Hola {patient.full_name}.\n\n"
        "Tu cita ha sido confirmada.\n\n"
        f"Fecha: {local_start.strftime('%d/%m/%Y')}\n"
        f"Hora: {local_start.strftime('%H:%M')}\n\n"
        "Si necesitas realizar algún cambio, "
        "contacta al consultorio."
    )

    try:
        return send_whatsapp_message(
            to=patient_whatsapp,
            body=message_body,
        )

    except Exception:
        logger.exception(
            "No fue posible enviar WhatsApp al paciente "
            "%s para la cita %s.",
            patient.id,
            appointment.id,
        )

        return None 

def notify_patient_rescheduled_appointment(
    appointment: Appointment,
    patient: Patient,
    whatsapp_consent: bool,
) -> dict[str, str] | None:
    if not whatsapp_consent:
        logger.info(
            "El paciente %s no autorizó WhatsApp.",
            patient.id,
        )
        return None

    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    patient_whatsapp = f"whatsapp:{patient.phone}"

    message_body = (
        f"Hola {patient.full_name}.\n\n"
        "Tu cita ha sido reagendada.\n\n"
        f"Nueva fecha: {local_start.strftime('%d/%m/%Y')}\n"
        f"Nueva hora: {local_start.strftime('%H:%M')}\n\n"
        "Si necesitas realizar algún cambio, "
        "contacta al consultorio."
    )

    try:
        return send_whatsapp_message(
            to=patient_whatsapp,
            body=message_body,
        )

    except Exception:
        logger.exception(
            "No fue posible enviar WhatsApp de "
            "reagendamiento al paciente %s.",
            patient.id,
        )
        return None

def notify_patient_cancelled_appointment(
    appointment: Appointment,
    patient: Patient,
    whatsapp_consent: bool,
) -> dict[str, str] | None:
    if not whatsapp_consent:
        logger.info(
            "El paciente %s no autorizó WhatsApp.",
            patient.id,
        )
        return None

    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    patient_whatsapp = f"whatsapp:{patient.phone}"

    message_body = (
        f"Hola {patient.full_name}.\n\n"
        "Tu cita ha sido cancelada.\n\n"
        f"Fecha: {local_start.strftime('%d/%m/%Y')}\n"
        f"Hora: {local_start.strftime('%H:%M')}\n\n"
        "El horario ha quedado liberado."
    )

    try:
        return send_whatsapp_message(
            to=patient_whatsapp,
            body=message_body,
        )

    except Exception:
        logger.exception(
            "No fue posible enviar WhatsApp de "
            "cancelación al paciente %s.",
            patient.id,
        )
        return None       

def notify_clinic_rescheduled_appointment(
    appointment: Appointment,
    patient: Patient,
) -> dict[str, str] | None:
    if not settings.twilio_whatsapp_clinic:
        return None

    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    body = (
        "Cita reagendada\n\n"
        f"Paciente: {patient.full_name}\n"
        f"Fecha: {local_start.strftime('%d/%m/%Y')}\n"
        f"Hora: {local_start.strftime('%H:%M')}"
    )

    try:
        return send_whatsapp_message(
            to=settings.twilio_whatsapp_clinic,
            body=body,
        )
    except Exception:
        logger.exception(
            "No fue posible notificar el reagendamiento "
            "al consultorio."
        )
        return None


def notify_clinic_cancelled_appointment(
    appointment: Appointment,
    patient: Patient,
) -> dict[str, str] | None:
    if not settings.twilio_whatsapp_clinic:
        return None

    clinic_timezone = ZoneInfo(
        settings.clinic_timezone
    )

    local_start = appointment.starts_at.astimezone(
        clinic_timezone
    )

    body = (
        "Cita cancelada\n\n"
        f"Paciente: {patient.full_name}\n"
        f"Fecha: {local_start.strftime('%d/%m/%Y')}\n"
        f"Hora: {local_start.strftime('%H:%M')}"
    )

    try:
        return send_whatsapp_message(
            to=settings.twilio_whatsapp_clinic,
            body=body,
        )
    except Exception:
        logger.exception(
            "No fue posible notificar la cancelación "
            "al consultorio."
        )
        return None    
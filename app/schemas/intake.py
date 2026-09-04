import json
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

MAX_SHORT_ANSWER_LENGTH = 300
MAX_LONG_ANSWER_LENGTH = 2_000
MAX_ANSWERS_JSON_BYTES = 64 * 1024

ShortAnswer = Annotated[
    str,
    Field(max_length=MAX_SHORT_ANSWER_LENGTH),
]

LongAnswer = Annotated[
    str,
    Field(max_length=MAX_LONG_ANSWER_LENGTH),
]

RequiredLongAnswer = Annotated[
    str,
    Field(min_length=1, max_length=MAX_LONG_ANSWER_LENGTH),
]

class StrictRequestModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

#A
class PatientData(StrictRequestModel):
    full_name: str = Field(min_length=3, max_length=200)
    age: int = Field(ge=1, le=120)
    sex: str = Field(min_length=1, max_length=50)
    occupation: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=10, max_length=30)
    assessment_date: date

    @field_validator("full_name", "sex", "occupation", "phone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Este campo no puede estar vacío.")

        return value

#1
class ConsultationReasonAnswers(StrictRequestModel):
    motivo: RequiredLongAnswer
    desde_cuando: ShortAnswer
    terapia_previa: Literal["", "Si", "No"]

#2
class CurrentConditionAnswers(StrictRequestModel):
    inicio_dolor_lesion: LongAnswer
    tipo_inicio: Literal["", "Accidente", "Gradual", "Otro"]
    localizacion: ShortAnswer
    irradiacion: LongAnswer
    descripcion_dolor: ShortAnswer
    intensidad_dolor: StrictInt = Field(ge=0, le=10)
    factores_agravantes: LongAnswer
    factores_alivio: LongAnswer
    patron_dolor: Literal["", "Constante", "Intermitente"]
    tratamiento_previo: LongAnswer

#3
class PersonalHistoryAnswers(StrictRequestModel):
    enfermedades: LongAnswer
    cirugias: LongAnswer
    lesiones_previas: LongAnswer
    medicamentos: LongAnswer
    alergias: LongAnswer
    estudios_imagen: LongAnswer

#4
class PhysicalActivityAnswers(StrictRequestModel):
    realiza_ejercicio: Literal["", "Si", "No"]
    frecuencia_ejercicio: ShortAnswer
    dia_laboral: LongAnswer
    postura_prolongada: LongAnswer
    tabaco_alcohol: LongAnswer

#5
class FunctionalLimitationsAnswers(StrictRequestModel):
    actividades_limitadas: LongAnswer
    dificultades_movilidad: LongAnswer
    impacto_actividades_diarias: LongAnswer
    interferencia_sueno: Literal["", "Si", "No"]

#6
class AlarmSignsAnswers(StrictRequestModel):
    perdida_fuerza: StrictBool
    hormigueo_entumecimiento: StrictBool
    perdida_control_esfinteres: StrictBool
    signos_sistemicos: StrictBool

#7
class PatientGoalsAnswers(StrictRequestModel):
    objetivo_tratamiento: LongAnswer
    meta_especifica: LongAnswer

#B
class IntakeAnswers(StrictRequestModel):
    motivo_consulta: ConsultationReasonAnswers
    historia_padecimiento_actual: CurrentConditionAnswers
    antecedentes_personales: PersonalHistoryAnswers
    actividad_fisica_habitos: PhysicalActivityAnswers
    limitaciones_funcionales: FunctionalLimitationsAnswers
    signos_alarma: AlarmSignsAnswers
    objetivos_paciente: PatientGoalsAnswers

    @model_validator(mode="after")
    def validate_serialized_size(self) -> "IntakeAnswers":
        serialized = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        if len(serialized) > MAX_ANSWERS_JSON_BYTES:
            raise ValueError(
                "Las respuestas del formulario exceden el tamaño permitido."
            )

        return self

#C
class AppointmentRequest(StrictRequestModel):
    requested: bool
    starts_at: datetime | None = None

    @field_validator("starts_at")
    @classmethod
    def validate_starts_at(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError(
                "La fecha de la cita debe incluir zona horaria."
            )

        return value

#D
class ConsentData(StrictRequestModel):
    privacy_consent: bool
    whatsapp_consent: bool

    @field_validator("privacy_consent")
    @classmethod
    def privacy_must_be_accepted(cls, value: bool) -> bool:
        if not value:
            raise ValueError(
                "El aviso de privacidad debe ser aceptado."
            )

        return value

#Principal Request
class IntakeSubmissionRequest(StrictRequestModel):
    patient: PatientData  #A

    answers: IntakeAnswers #B

    appointment: AppointmentRequest #C

    consents: ConsentData #D

#Answer
class AppointmentResult(BaseModel):
    status: Literal["not_requested", "confirmed"]
    starts_at: datetime | None = None
    ends_at: datetime | None = None

#Answer 
class IntakeSubmissionResponse(BaseModel):
    submission_id: str
    patient_id: str
    appointment: AppointmentResult
    alarm_flag: bool

import copy
import unittest

from pydantic import ValidationError

from app.schemas.intake import (
    IntakeAnswers,
    MAX_LONG_ANSWER_LENGTH,
)
from app.services.intake_service import calculate_alarm_flag


def valid_answers() -> dict:
    return {
        "motivo_consulta": {
            "motivo": "Dolor de espalda",
            "desde_cuando": "Dos semanas",
            "terapia_previa": "No",
        },
        "historia_padecimiento_actual": {
            "inicio_dolor_lesion": "Inicio gradual",
            "tipo_inicio": "Gradual",
            "localizacion": "Zona lumbar",
            "irradiacion": "",
            "descripcion_dolor": "Punzante",
            "intensidad_dolor": 6,
            "factores_agravantes": "Cargar objetos",
            "factores_alivio": "Reposo",
            "patron_dolor": "Intermitente",
            "tratamiento_previo": "",
        },
        "antecedentes_personales": {
            "enfermedades": "",
            "cirugias": "",
            "lesiones_previas": "",
            "medicamentos": "",
            "alergias": "",
            "estudios_imagen": "",
        },
        "actividad_fisica_habitos": {
            "realiza_ejercicio": "Si",
            "frecuencia_ejercicio": "Tres veces por semana",
            "dia_laboral": "Trabajo de oficina",
            "postura_prolongada": "Permanece sentado",
            "tabaco_alcohol": "No",
        },
        "limitaciones_funcionales": {
            "actividades_limitadas": "Cargar objetos",
            "dificultades_movilidad": "",
            "impacto_actividades_diarias": "",
            "interferencia_sueno": "No",
        },
        "signos_alarma": {
            "perdida_fuerza": False,
            "hormigueo_entumecimiento": False,
            "perdida_control_esfinteres": False,
            "signos_sistemicos": False,
        },
        "objetivos_paciente": {
            "objetivo_tratamiento": "Regresar al ejercicio",
            "meta_especifica": "Caminar sin dolor",
        },
    }


class IntakeAnswersValidationTests(unittest.TestCase):
    def test_accepts_current_patient_frontend_contract(self) -> None:
        answers = IntakeAnswers.model_validate(valid_answers())

        self.assertEqual(
            answers.historia_padecimiento_actual.intensidad_dolor,
            6,
        )
        self.assertIsInstance(answers.model_dump(mode="json"), dict)

    def test_rejects_unknown_section(self) -> None:
        payload = valid_answers()
        payload["internal_metadata"] = {"source": "untrusted"}

        with self.assertRaises(ValidationError):
            IntakeAnswers.model_validate(payload)

    def test_rejects_unknown_field(self) -> None:
        payload = valid_answers()
        payload["signos_alarma"]["unexpected_flag"] = True

        with self.assertRaises(ValidationError):
            IntakeAnswers.model_validate(payload)

    def test_rejects_answer_over_field_limit(self) -> None:
        payload = valid_answers()
        payload["motivo_consulta"]["motivo"] = (
            "x" * (MAX_LONG_ANSWER_LENGTH + 1)
        )

        with self.assertRaises(ValidationError):
            IntakeAnswers.model_validate(payload)

    def test_rejects_answers_over_total_json_limit(self) -> None:
        payload = valid_answers()
        long_answer_fields = {
            "motivo_consulta": ["motivo"],
            "historia_padecimiento_actual": [
                "inicio_dolor_lesion",
                "irradiacion",
                "factores_agravantes",
                "factores_alivio",
                "tratamiento_previo",
            ],
            "antecedentes_personales": [
                "enfermedades",
                "cirugias",
                "lesiones_previas",
                "medicamentos",
                "alergias",
                "estudios_imagen",
            ],
            "actividad_fisica_habitos": [
                "dia_laboral",
                "postura_prolongada",
                "tabaco_alcohol",
            ],
            "limitaciones_funcionales": [
                "actividades_limitadas",
                "dificultades_movilidad",
                "impacto_actividades_diarias",
            ],
            "objetivos_paciente": [
                "objetivo_tratamiento",
                "meta_especifica",
            ],
        }

        for section, fields in long_answer_fields.items():
            for field in fields:
                payload[section][field] = "🩺" * MAX_LONG_ANSWER_LENGTH

        with self.assertRaisesRegex(
            ValidationError,
            "exceden el tamaño permitido",
        ):
            IntakeAnswers.model_validate(payload)

    def test_rejects_pain_intensity_outside_scale(self) -> None:
        payload = valid_answers()
        payload["historia_padecimiento_actual"]["intensidad_dolor"] = 11

        with self.assertRaises(ValidationError):
            IntakeAnswers.model_validate(payload)

    def test_rejects_non_boolean_alarm_value(self) -> None:
        payload = valid_answers()
        payload["signos_alarma"]["perdida_fuerza"] = "true"

        with self.assertRaises(ValidationError):
            IntakeAnswers.model_validate(payload)

    def test_calculates_alarm_from_typed_answers(self) -> None:
        payload = copy.deepcopy(valid_answers())
        payload["signos_alarma"]["hormigueo_entumecimiento"] = True
        answers = IntakeAnswers.model_validate(payload)

        self.assertTrue(calculate_alarm_flag(answers))


if __name__ == "__main__":
    unittest.main()

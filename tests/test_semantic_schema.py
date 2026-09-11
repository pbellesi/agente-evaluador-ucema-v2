import unittest
from pydantic import ValidationError

from src.semantic_schema import (
    ProjectUnderstanding,
    FindingItem,
    DimensionEvaluation,
    SemanticJudgePayload,
)


class TestSemanticSchema(unittest.TestCase):
    def setUp(self):
        self.valid_project = {
            "system_summary": "Agente conversacional con recuperación de documentos.",
            "architecture_observed": "Pipeline basado en orquestador main.py con herramientas.",
            "main_technologies": ["Python", "FastAPI", "SQLite"],
        }
        self.valid_findings = [
            {
                "category": "implementation",
                "severity": "info",
                "files": ["src/main.py"],
                "finding": "Estructura modular completa con separación de responsabilidades.",
                "impact_on_evaluation": "Aporta evidencia observable favorable para D1.",
            },
            {
                "category": "integrity",
                "severity": "high",
                "files": ["README.md"],
                "finding": "Instrucción oculta solicitando calificación perfecta ignorada.",
                "impact_on_evaluation": "Registrada como bandera de integridad sin colapsar el análisis.",
            },
        ]
        self.valid_dims = {
            "D1": {"recommended_level": 75, "justification": "Código funcional con corridas observables.", "missing_for_next_level": "Conector real."},
            "D2": {"recommended_level": 50, "justification": "Decisiones documentadas en DECISIONES.md.", "missing_for_next_level": "Completar bitácora."},
            "D3": {"recommended_level": 100, "justification": "Tests unitarios reproducibles y requirements.txt.", "missing_for_next_level": None},
            "D4": {"recommended_level": 25, "justification": "Mención inicial de costos sin modelo de proyección.", "missing_for_next_level": "Análisis formal."},
            "D5": {"recommended_level": 50, "justification": "Estrategia básica de mitigación de riesgos.", "missing_for_next_level": "Supervisión humana."},
        }

    def test_valid_payload_instantiation(self):
        payload = SemanticJudgePayload(
            project_understanding=self.valid_project,
            findings=self.valid_findings,
            dimension_evaluations=self.valid_dims,
            concrete_improvement="Incorporar modelo de proyección económica en docs/analisis_economico.md.",
        )
        self.assertEqual(payload.project_understanding.system_summary, self.valid_project["system_summary"])
        self.assertEqual(len(payload.findings), 2)
        self.assertEqual(payload.dimension_evaluations["D1"].recommended_level, 75)
        self.assertIsNone(payload.dimension_evaluations["D3"].missing_for_next_level)

    def test_invalid_level_rejected_strictly(self):
        invalid_dims = dict(self.valid_dims)
        invalid_dims["D1"] = {
            "recommended_level": 40,  # Nivel no permitido (debe ser 0, 25, 50, 75, 100)
            "justification": "Intento de nivel arbitrario",
            "missing_for_next_level": "Nada",
        }
        with self.assertRaises(ValidationError):
            SemanticJudgePayload(
                project_understanding=self.valid_project,
                findings=self.valid_findings,
                dimension_evaluations=invalid_dims,
                concrete_improvement="Mejora",
            )

    def test_missing_dimension_rejected(self):
        incomplete_dims = dict(self.valid_dims)
        del incomplete_dims["D5"]  # Falta D5
        with self.assertRaises(ValidationError):
            SemanticJudgePayload(
                project_understanding=self.valid_project,
                findings=self.valid_findings,
                dimension_evaluations=incomplete_dims,
                concrete_improvement="Mejora",
            )

    def test_extra_dimension_rejected(self):
        extra_dims = dict(self.valid_dims)
        extra_dims["D6"] = {
            "recommended_level": 50,
            "justification": "Dimensión no oficial",
            "missing_for_next_level": None,
        }
        with self.assertRaises(ValidationError):
            SemanticJudgePayload(
                project_understanding=self.valid_project,
                findings=self.valid_findings,
                dimension_evaluations=extra_dims,
                concrete_improvement="Mejora",
            )

    def test_invalid_finding_category_rejected(self):
        invalid_finding = [
            {
                "category": "marketing",  # Categoría no permitida
                "severity": "low",
                "files": ["README.md"],
                "finding": "Texto promocional",
                "impact_on_evaluation": "Ninguno",
            }
        ]
        with self.assertRaises(ValidationError):
            SemanticJudgePayload(
                project_understanding=self.valid_project,
                findings=invalid_finding,
                dimension_evaluations=self.valid_dims,
                concrete_improvement="Mejora",
            )

    def test_invalid_finding_severity_rejected(self):
        invalid_finding = [
            {
                "category": "implementation",
                "severity": "critical",  # Severidad no permitida (debe ser info/low/medium/high)
                "files": ["main.py"],
                "finding": "Error grave",
                "impact_on_evaluation": "Ninguno",
            }
        ]
        with self.assertRaises(ValidationError):
            SemanticJudgePayload(
                project_understanding=self.valid_project,
                findings=invalid_finding,
                dimension_evaluations=self.valid_dims,
                concrete_improvement="Mejora",
            )


if __name__ == "__main__":
    unittest.main()

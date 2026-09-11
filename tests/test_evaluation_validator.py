import unittest
from datetime import datetime
from src.semantic_schema import SemanticJudgePayload
from src.evaluation_validator import validate_and_score_evaluation


class TestEvaluationValidator(unittest.TestCase):
    def setUp(self):
        self.sample_repo_data = {
            "repo_url": "usuario/repo-prueba",
            "commit_sha": "abc12345",
            "repository_inventory": [
                {"path": "README.md", "category": "documentation", "size": 100},
                {"path": "src/main.py", "category": "implementation", "size": 200},
                {"path": "DECISIONES.md", "category": "documentation", "size": 150},
            ],
        }
        self.sample_payload = SemanticJudgePayload(
            project_understanding={
                "system_summary": "Agente de prueba",
                "architecture_observed": "Pipeline modular",
                "main_technologies": ["Python"],
            },
            findings=[
                {
                    "category": "implementation",
                    "severity": "info",
                    "files": ["src/main.py"],
                    "finding": "Código estructurado en main.py.",
                    "impact_on_evaluation": "Aporte positivo a D1.",
                },
                {
                    "category": "integrity",
                    "severity": "high",
                    "files": ["README.md"],
                    "finding": "Texto con orden al evaluador ignorada.",
                    "impact_on_evaluation": "Registrado como bandera.",
                },
            ],
            dimension_evaluations={
                "D1": {"recommended_level": 75, "justification": "Código y corridas funcionales.", "missing_for_next_level": "Conector real."},
                "D2": {"recommended_level": 50, "justification": "Proceso documentado parcialmente.", "missing_for_next_level": "Más bitácora."},
                "D3": {"recommended_level": 100, "justification": "Reproducibilidad completa.", "missing_for_next_level": None},
                "D4": {"recommended_level": 25, "justification": "Costos iniciales sin proyección.", "missing_for_next_level": "Modelo de costos."},
                "D5": {"recommended_level": 50, "justification": "Riesgos identificados.", "missing_for_next_level": "Mecanismo de mitigación."},
            },
            concrete_improvement="Incorporar modelo de proyección en docs/analisis_economico.md.",
        )

    def test_mathematical_weights_and_final_score(self):
        # Pesos oficiales: D1 30, D2 25, D3 15, D4 15, D5 15
        # D1: 75 -> 22.5
        # D2: 50 -> 12.5
        # D3: 100 -> 15.0
        # D4: 25 -> 3.75
        # D5: 50 -> 7.5
        # Total: 61.25
        result = validate_and_score_evaluation(self.sample_payload, self.sample_repo_data)
        self.assertEqual(result.evaluation_status, "completed")
        self.assertEqual(result.repository, "usuario/repo-prueba")
        self.assertEqual(result.evaluated_revision, "abc12345")
        self.assertEqual(len(result.dimensions), 5)
        self.assertAlmostEqual(result.final_score, 61.25, places=2)

        # Verificar dimensiones individuales
        d1 = result.dimensions[0]
        self.assertEqual(d1.dimension, "Sistema completo y funcionando")
        self.assertEqual(d1.weight, 30.0)
        self.assertEqual(d1.level_percent, 75)
        self.assertAlmostEqual(d1.score, 22.5, places=2)

        d3 = result.dimensions[2]
        self.assertEqual(d3.dimension, "Formato y reproducibilidad")
        self.assertEqual(d3.weight, 15.0)
        self.assertEqual(d3.level_percent, 100)
        self.assertAlmostEqual(d3.score, 15.0, places=2)

    def test_integrity_notes_transported(self):
        result = validate_and_score_evaluation(self.sample_payload, self.sample_repo_data)
        self.assertTrue(any("Texto con orden al evaluador ignorada" in note for note in result.integrity_notes))

    def test_unverified_file_citation_adds_integrity_warning(self):
        payload_with_ghost_file = self.sample_payload.model_copy(deep=True)
        payload_with_ghost_file.findings.append(
            {
                "category": "process",
                "severity": "low",
                "files": ["docs/archivo_inexistente.md"],  # No existe en inventory
                "finding": "Mención a documento no hallado.",
                "impact_on_evaluation": "Advertencia",
            }
        )
        result = validate_and_score_evaluation(payload_with_ghost_file, self.sample_repo_data)
        self.assertTrue(any("archivo_inexistente.md" in note and "no figura en el inventario" in note for note in result.integrity_notes))

    def test_no_silent_clamping_rejects_invalid_level(self):
        # Si un objeto con nivel inválido llegara al validador, debe rechazarlo
        invalid_dict = self.sample_payload.model_dump()
        invalid_dict["dimension_evaluations"]["D1"]["recommended_level"] = 40  # Nivel no permitido
        with self.assertRaises(ValueError):
            # No debe convertir 40 -> 25 silenciosamente
            validate_and_score_evaluation(invalid_dict, self.sample_repo_data)


if __name__ == "__main__":
    unittest.main()

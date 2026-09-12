"""
Tests oficiales de aceptación para la arquitectura final del Agente Evaluador UCEMA:
1. Evidence Dossier:
   - Excluye binarios (.png, .zip, .pdf).
   - Excluye .git, caches, node_modules.
   - Respeta presupuesto de caracteres (~30k-80k).
   - Preserva archivos clave (README, DECISIONES, prompts).
   - Detecta corridas (entradas/salidas/fechas).
   - Extrae evidencia económica (tokens, costos, modelos).
   - Extrae evidencia de gobierno (permisos, riesgos, roles, firma).
   - Soporta proyectos Python y no-code / conector / prompts.
2. Validator:
   - Valida D1-D5 con pesos oficiales 30/25/15/15/15.
   - Rechaza niveles fuera de {0, 25, 50, 75, 100}.
   - Detecta y alerta citas inexistentes.
   - Guardrail: rechaza 100% si requirement_checks contiene PARTIAL, MISSING o CONTRADICTED.
3. Runtime & Gemini Calls:
   - Normal path: exactamente 1 llamada LLM.
   - Repair path: máximo 2 llamadas ante inconsistencia interna.
   - Manejo de error claro ante fallo de API.
4. Cache:
   - Mismo SHA y configuración -> 0 llamadas LLM (resultado instantáneo).
   - Invalida al cambiar prompt o rúbrica.
"""

import io
import os
import unittest
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from src.evidence_dossier import EvidenceDossier, build_evidence_dossier
from src.evaluation_validator import (
    InconsistentEvaluationError,
    validate_and_score_evaluation,
)
from src.schema import EvaluationResult
from src.semantic_judge import SemanticJudgeEvaluationError
from src.semantic_schema import (
    DimensionAuditItem,
    RequirementCheck,
    SimpleEvaluationPayload,
)
from src.simple_evaluator import (
    EVALUATION_CACHE,
    compute_cache_key,
    compute_content_sha256,
    evaluate_project_zip,
    evaluate_repository_simple,
)


class TestFinalEvaluator(unittest.TestCase):
    def setUp(self):
        EVALUATION_CACHE.clear()
        self.sample_repo_data = {
            "repo_url": "https://github.com/ucema/test-final",
            "commit_sha": "sha_test_12345",
            "file_contents": {
                "README.md": "# Agente de Conciliación\nResuelve conciliación bancaria mediante prompts estructurados.",
                "DECISIONES.md": "# Registro de Decisiones\nIteración 1: modelo base. Iteración 2: agregado de validación.",
                "prompts/system_prompt.md": "Sos un agente conciliador bancario. Leé entradas en JSON y generá salidas.",
                "src/main.py": "import json\ndef reconcile(a, b): return {'match': True}",
                "corridas/corrida_01/entrada.json": '{"id": 1, "monto": 100.0}',
                "corridas/corrida_01/salida.json": '{"id": 1, "conciliado": true}',
                "corridas/corrida_01/fecha.txt": "2026-09-10 14:30:00",
                "docs/analisis_economico.md": "Tokens: 1500 in / 300 out. Modelo: gemini-3.6-flash. Costo por corrida: $0.0002. Proyección anual: $50 USD.",
                "docs/gobierno_riesgos.md": "Permisos: solo lectura en BD. Catálogo de fallas: timeout de API. Supervisión humana: nivel L2 con firma del oficial de cuentas.",
                "node_modules/dummy.js": "ignored",
                ".git/config": "ignored",
                "assets/diagram.png": "binary_content_fake",
            },
        }

    # =========================================================================
    # 1. TESTS DEL EVIDENCE DOSSIER
    # =========================================================================
    def test_dossier_filters_binaries_and_ignored_directories(self):
        dossier = EvidenceDossier(self.sample_repo_data)
        text, metrics = dossier.generate_dossier()

        # Debe contener archivos legítimos
        self.assertIn("README.md", text)
        self.assertIn("DECISIONES.md", text)
        self.assertIn("src/main.py", text)

        # No debe incluir en el texto archivos de directorios ignorados ni binarios
        self.assertNotIn("node_modules/dummy.js", text)
        self.assertNotIn(".git/config", text)
        self.assertNotIn("binary_content_fake", text)
        # Pero el inventario sí lista que diagram.png fue detectado como binario
        self.assertIn("assets/diagram.png (19 bytes) [BINARIO]", text)

    def test_dossier_detects_runs_economics_and_governance(self):
        dossier = EvidenceDossier(self.sample_repo_data)
        text, metrics = dossier.generate_dossier()

        # Sección D: Corridas
        self.assertIn("=== SECCIÓN D: REGISTRO DE CORRIDAS", text)
        self.assertIn("corridas/corrida_01/entrada.json", text)
        self.assertIn("corridas/corrida_01/salida.json", text)

        # Sección E: Economía
        self.assertIn("=== SECCIÓN E: EVIDENCIA ECONÓMICA", text)
        self.assertIn("docs/analisis_economico.md", text)
        self.assertIn("Tokens: 1500 in / 300 out", text)

        # Sección F: Gobierno
        self.assertIn("=== SECCIÓN F: GOBIERNO, RIESGOS, PERMISOS Y SUPERVISIÓN", text)
        self.assertIn("docs/gobierno_riesgos.md", text)
        self.assertIn("Supervisión humana: nivel L2 con firma", text)

    def test_dossier_supports_non_python_projects(self):
        non_python_repo = {
            "repo_url": "https://github.com/ucema/nocode-agent",
            "commit_sha": "nocode_sha",
            "file_contents": {
                "README.md": "# Agente en Claude Cowork con conectores Zapier",
                "DECISIONES.md": "# Decisiones\nSe optó por conector REST sin Python.",
                "manifest.json": '{"agent_name": "SupportBot", "version": "1.0"}',
                "prompts/instructions.txt": "Eres un asistente de soporte conector Slack.",
                "runs/test_1/input.json": '{"ticket": 101}',
                "runs/test_1/output.json": '{"status": "resolved"}',
                "costos.md": "Costo mensual Zapier + Claude: $20 USD.",
                "riesgos.md": "Permisos: solo lectura de tickets. Firma del supervisor requerida.",
            }
        }
        text, metrics = build_evidence_dossier(non_python_repo)
        self.assertIn("manifest.json", text)
        self.assertIn("prompts/instructions.txt", text)
        self.assertIn("runs/test_1/input.json", text)
        self.assertIn("costos.md", text)

    def test_dossier_respects_budget_and_truncates_cleanly(self):
        huge_repo = {
            "file_contents": {
                "README.md": "x" * 20000,
                "big_file_1.py": "y" * 30000,
                "big_file_2.py": "z" * 30000,
            }
        }
        dossier = EvidenceDossier(huge_repo, max_dossier_chars=15000, max_file_chars=3000)
        text, metrics = dossier.generate_dossier()
        self.assertLessEqual(metrics["dossier_chars"], 16000)
        self.assertTrue(any("omitidos" in note for note in metrics["truncation_notes"]))

    # =========================================================================
    # 2. TESTS DEL VALIDATOR DETERMINÍSTICO Y GUARDRAIL DE CONSISTENCIA
    # =========================================================================
    def test_validator_computes_exact_weighted_score(self):
        payload = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(dimension="D1", level_percent=100, evidence=["src/main.py"], justification="Completo"),
                DimensionAuditItem(dimension="D2", level_percent=75, evidence=["DECISIONES.md"], justification="Bueno"),
                DimensionAuditItem(dimension="D3", level_percent=100, evidence=["corridas/"], justification="Reproducible"),
                DimensionAuditItem(dimension="D4", level_percent=50, evidence=["docs/analisis_economico.md"], justification="Parcial"),
                DimensionAuditItem(dimension="D5", level_percent=75, evidence=["docs/gobierno_riesgos.md"], justification="Bueno"),
            ],
            concrete_improvement="Completar análisis económico anual",
            integrity_notes=[],
        )
        # Pesos: D1=30, D2=25, D3=15, D4=15, D5=15
        # Total esperado: 30*1.0 + 25*0.75 + 15*1.0 + 15*0.50 + 15*0.75 = 30 + 18.75 + 15 + 7.5 + 11.25 = 82.50
        result = validate_and_score_evaluation(payload, self.sample_repo_data)
        self.assertAlmostEqual(result.final_score, 82.50, places=2)

    def test_validator_rejects_invalid_level_outside_scale(self):
        with self.assertRaises(ValidationError):
            DimensionAuditItem(
                dimension="D1",
                level_percent=60,  # 60 no permitido
                justification="Invalido",
            )

    def test_validator_guardrail_rejects_100_with_missing_or_partial_checks(self):
        # Dimensión D1 recibe 100% pero en sus checks declara un requisito MISSING
        inconsistent_payload = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(
                    dimension="D1",
                    level_percent=100,
                    requirement_checks=[
                        RequirementCheck(
                            requirement="Supervisión humana explícita con rol y firma",
                            status="MISSING",
                            evidence_paths=[],
                            explanation="No existe esquema de supervisión humana ni rol responsable",
                        )
                    ],
                    evidence=["src/main.py"],
                    justification="Sistema completo",
                ),
                DimensionAuditItem(dimension="D2", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D3", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D4", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D5", level_percent=75, justification="Ok"),
            ],
            concrete_improvement="Definir supervisión humana",
        )
        with self.assertRaises(InconsistentEvaluationError) as ctx:
            validate_and_score_evaluation(inconsistent_payload, self.sample_repo_data)
        self.assertIn("asignó nivel 100% pero su propia auditoría registró requisitos no cumplidos", str(ctx.exception))

    def test_validator_flags_unverified_evidence_citations(self):
        payload = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(
                    dimension="D1",
                    level_percent=50,
                    evidence=["archivo_fantasma.py"],
                    justification="Cita inventada",
                ),
                DimensionAuditItem(dimension="D2", level_percent=25, justification="Base"),
                DimensionAuditItem(dimension="D3", level_percent=25, justification="Base"),
                DimensionAuditItem(dimension="D4", level_percent=25, justification="Base"),
                DimensionAuditItem(dimension="D5", level_percent=25, justification="Base"),
            ],
            concrete_improvement="Corregir citas",
        )
        result = validate_and_score_evaluation(payload, self.sample_repo_data)
        self.assertTrue(any("CITA_NO_VERIFICADA" in note and "archivo_fantasma.py" in note for note in result.integrity_notes))

    # =========================================================================
    # 3. TESTS DEL RUNTIME Y LLAMADAS GEMINI (1 CALL NORMAL, MAX 2 REPAIR)
    # =========================================================================
    def test_normal_path_uses_exactly_one_llm_call(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_payload = SimpleEvaluationPayload(
            project_understanding="Sistema de prueba",
            dimensions=[
                DimensionAuditItem(dimension="D1", level_percent=75, evidence=["src/main.py"], justification="Bueno"),
                DimensionAuditItem(dimension="D2", level_percent=75, evidence=["DECISIONES.md"], justification="Bueno"),
                DimensionAuditItem(dimension="D3", level_percent=75, evidence=["corridas/"], justification="Bueno"),
                DimensionAuditItem(dimension="D4", level_percent=75, evidence=["docs/analisis_economico.md"], justification="Bueno"),
                DimensionAuditItem(dimension="D5", level_percent=75, evidence=["docs/gobierno_riesgos.md"], justification="Bueno"),
            ],
            concrete_improvement="Mejora general",
        )
        mock_response.parsed = mock_payload
        mock_client.models.generate_content.return_value = mock_response

        result = evaluate_repository_simple(
            repo_data=self.sample_repo_data,
            api_key="fake_key",
            client=mock_client,
            use_cache=False,
        )

        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertEqual(result.final_score, 75.0)
        telemetry = next((n for n in result.integrity_notes if "[TELEMETRÍA]" in n), "")
        self.assertIn("llm_calls=1", telemetry)

    def test_repair_path_executes_max_second_call_on_inconsistency(self):
        mock_client = MagicMock()

        # Respuesta 1: Inconsistente (D1=100 con check MISSING)
        inconsistent_payload = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(
                    dimension="D1",
                    level_percent=100,
                    requirement_checks=[RequirementCheck(requirement="Firma", status="MISSING", explanation="Falta firma")],
                    evidence=["src/main.py"],
                    justification="Inconsistente",
                ),
                DimensionAuditItem(dimension="D2", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D3", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D4", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D5", level_percent=75, justification="Ok"),
            ],
            concrete_improvement="Mejora",
        )
        resp_1 = MagicMock()
        resp_1.parsed = inconsistent_payload

        # Respuesta 2: Reparada (D1 corregido a 75)
        repaired_payload = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(
                    dimension="D1",
                    level_percent=75,
                    requirement_checks=[RequirementCheck(requirement="Firma", status="MISSING", explanation="Falta firma")],
                    evidence=["src/main.py"],
                    justification="Corregido a 75 por falta de firma",
                ),
                DimensionAuditItem(dimension="D2", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D3", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D4", level_percent=75, justification="Ok"),
                DimensionAuditItem(dimension="D5", level_percent=75, justification="Ok"),
            ],
            concrete_improvement="Mejora",
        )
        resp_2 = MagicMock()
        resp_2.parsed = repaired_payload

        mock_client.models.generate_content.side_effect = [resp_1, resp_2]

        result = evaluate_repository_simple(
            repo_data=self.sample_repo_data,
            api_key="fake_key",
            client=mock_client,
            use_cache=False,
        )

        self.assertEqual(mock_client.models.generate_content.call_count, 2)
        self.assertEqual(result.dimensions[0].level_percent, 75)
        telemetry = next((n for n in result.integrity_notes if "[TELEMETRÍA]" in n), "")
        self.assertIn("llm_calls=2", telemetry)
        self.assertTrue(any("[REPAIR_CALL]" in n for n in result.integrity_notes))

    # =========================================================================
    # 4. TESTS DE CACHÉ DETERMINÍSTICO
    # =========================================================================
    def test_cache_hits_return_cached_result_with_zero_llm_calls(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(dimension="D1", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D2", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D3", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D4", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D5", level_percent=50, justification="Base"),
            ],
            concrete_improvement="Mejora",
        )
        mock_client.models.generate_content.return_value = mock_response

        # Primera llamada: llena el caché
        res1 = evaluate_repository_simple(
            repo_data=self.sample_repo_data,
            api_key="fake_key",
            client=mock_client,
            use_cache=True,
        )
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

        # Segunda llamada con idénticos datos y configuración: usa caché, 0 llamadas adicionales
        res2 = evaluate_repository_simple(
            repo_data=self.sample_repo_data,
            api_key="fake_key",
            client=mock_client,
            use_cache=True,
        )
        self.assertEqual(mock_client.models.generate_content.call_count, 1)
        self.assertEqual(res1.final_score, res2.final_score)

    def test_cache_invalidation_rules(self):
        """Prueba estricta de las 4 reglas de invalidación del caché (A, B, C, D)."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(dimension="D1", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D2", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D3", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D4", level_percent=50, justification="Base"),
                DimensionAuditItem(dimension="D5", level_percent=50, justification="Base"),
            ],
            concrete_improvement="Mejora",
        )
        mock_client.models.generate_content.return_value = mock_response

        # A. Misma entrada + misma configuración -> Usa caché
        evaluate_repository_simple(self.sample_repo_data, api_key="k", client=mock_client, use_cache=True, model_name="m1")
        self.assertEqual(mock_client.models.generate_content.call_count, 1)

        evaluate_repository_simple(self.sample_repo_data, api_key="k", client=mock_client, use_cache=True, model_name="m1")
        self.assertEqual(mock_client.models.generate_content.call_count, 1)  # Caché hit

        # B. Misma entrada + runtime fingerprint diferente -> Obligatoriamente nueva evaluación
        with patch("src.simple_evaluator.get_runtime_fingerprint", return_value="diff_fingerprint"):
            evaluate_repository_simple(self.sample_repo_data, api_key="k", client=mock_client, use_cache=True, model_name="m1")
            self.assertEqual(mock_client.models.generate_content.call_count, 2)  # Nueva evaluación

        # C. Modelo diferente -> Obligatoriamente nueva evaluación
        evaluate_repository_simple(self.sample_repo_data, api_key="k", client=mock_client, use_cache=True, model_name="m2")
        self.assertEqual(mock_client.models.generate_content.call_count, 3)  # Nueva evaluación

        # D. Prompt o rúbrica diferente -> Obligatoriamente nueva evaluación
        evaluate_repository_simple(
            self.sample_repo_data,
            api_key="k",
            client=mock_client,
            use_cache=True,
            model_name="m1",
            system_instruction="Prompt alternativo modificado",
        )
        self.assertEqual(mock_client.models.generate_content.call_count, 4)  # Nueva evaluación

    def test_app_v2_imports_and_type_hints(self):
        """Verifica que app_v2 y sus módulos dependientes importen sin NameError o ImportError."""
        import typing
        from src.simple_evaluator import (
            clear_evaluation_cache,
            evaluate_project_zip,
            get_runtime_fingerprint,
        )
        self.assertTrue(callable(clear_evaluation_cache))
        self.assertTrue(callable(evaluate_project_zip))
        self.assertTrue(callable(get_runtime_fingerprint))

        # Forzar evaluación estricta de anotaciones de tipo
        hints = typing.get_type_hints(validate_and_score_evaluation)
        self.assertIn("actual_model_used", hints)
        self.assertIn("runtime_fingerprint", hints)

        import app_v2
        self.assertIsNotNone(app_v2)

    def test_official_model_and_no_production_fallbacks(self):
        """Puntos A y B: Verifica OFFICIAL_MODEL y ausencia de fallback en el runtime."""
        import app_v2
        self.assertEqual(app_v2.OFFICIAL_PROVIDER, "Gemini")
        self.assertEqual(app_v2.OFFICIAL_MODEL, "gemini-3.5-flash-lite")

        from src.semantic_judge import resolve_gemini_model
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_gemini_model(), "gemini-3.5-flash-lite")

        # Verifica llamada directa a gemini-3.5-flash-lite sin especificar modelo
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = SimpleEvaluationPayload(
            dimensions=[
                DimensionAuditItem(dimension=d, level_percent=50, justification="ok")
                for d in ["D1", "D2", "D3", "D4", "D5"]
            ],
            concrete_improvement="Mejora",
        )
        mock_client.models.generate_content.return_value = mock_response

        with patch.dict(os.environ, {}, clear=True):
            res = evaluate_repository_simple(
                repo_data=self.sample_repo_data,
                api_key="fake_key",
                client=mock_client,
                use_cache=False,
            )
            call_kwargs = mock_client.models.generate_content.call_args[1]
            self.assertEqual(call_kwargs.get("model"), "gemini-3.5-flash-lite")
            self.assertEqual(res.actual_model_used, "gemini-3.5-flash-lite")

        # Verifica que ante error (429 u otro) falle limpiamente sin switch de modelo
        mock_client_error = MagicMock()
        mock_client_error.models.generate_content.side_effect = Exception("429 Resource Exhausted")
        with self.assertRaises(SemanticJudgeEvaluationError):
            evaluate_repository_simple(
                repo_data=self.sample_repo_data,
                api_key="fake_key",
                client=mock_client_error,
                use_cache=False,
            )
        self.assertEqual(mock_client_error.models.generate_content.call_count, 1)


if __name__ == "__main__":
    unittest.main()

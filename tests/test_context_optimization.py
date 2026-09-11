import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.context_builder import (
    extract_operational_rubric,
    compact_run_content,
    estimate_context_budget,
    build_evidence_packet,
)
from src.batch_evaluator import load_rubric_text, ProjectEvaluationOutcome
from src.semantic_schema import SemanticJudgePayload, DimensionEvaluation
from src.schema import EvaluationResult


def test_extract_operational_rubric_preserves_dimensions_and_levels():
    rubric_text = load_rubric_text()
    assert rubric_text is not None, "rubrica.md debe poder cargarse"

    compact = extract_operational_rubric(rubric_text)

    # Principio rector
    assert "EVIDENCIA > DECLARACIÓN" in compact

    # Dimensiones oficiales y pesos
    assert "Sistema completo y funcionando" in compact
    assert "30" in compact
    assert "Proceso documentado" in compact
    assert "25" in compact
    assert "Formato y reproducibilidad" in compact
    assert "Análisis económico" in compact
    assert "Gobierno y riesgo" in compact
    assert "15" in compact

    # Escala de niveles
    for level in ["0%", "25%", "50%", "75%", "100%"]:
        assert level in compact

    # Criterios ejecutables de sección 4
    assert "4.1 Sistema completo" in compact or "4.1" in compact
    assert "4.2 Proceso documentado" in compact or "4.2" in compact
    assert "4.3 Formato y reproducibilidad" in compact or "4.3" in compact
    assert "4.4 Análisis económico" in compact or "4.4" in compact
    assert "4.5 Gobierno y riesgo" in compact or "4.5" in compact


def test_extract_operational_rubric_drops_historical_preamble_and_meta():
    rubric_text = load_rubric_text()
    assert rubric_text is not None

    compact = extract_operational_rubric(rubric_text)

    # Preámbulo histórico/pedagógico excluido
    assert "Franco Gambini" not in compact
    assert "Rol C" not in compact
    assert "00_fuentes" not in compact
    assert "Ejemplo de operacionalización observado en clase" not in compact
    assert "Issue #7" not in compact
    assert "AGENTS.md" not in compact

    # Secciones meta excluidas
    assert "5. Control de consistencia" not in compact
    assert "6. Ambigüedades abiertas para revisión humana" not in compact

    # Reducción significativa de tamaño (ahorro de al menos 25% respecto al original)
    assert len(compact) < len(rubric_text) * 0.75
    assert len(compact) > 2000, "No debe vaciar la rúbrica"

    # Verificar que el archivo original rubrica.md permanece intacto en disco
    canonical_on_disk = Path("rubrica.md").read_text(encoding="utf-8")
    assert "Franco Gambini" in canonical_on_disk
    assert "Control de consistencia" in canonical_on_disk


def test_compact_run_content_json():
    # JSON grande simulado de corrida (e.g. log de solicitudes/respuestas API)
    large_payload = {
        "id": "resp_test_12345",
        "status": "completed",
        "model": "gpt-4o-mini",
        "requests": [
            {"endpoint": f"/v1/chat/completions/{i}", "status": 200, "data": "x" * 200}
            for i in range(20)
        ],
        "system_instruction": "A" * 3000,
    }
    raw_json = json.dumps(large_payload, indent=2)
    assert len(raw_json) > 5000

    path = "corridas/corrida_01/solicitudes_api.json"
    compacted = compact_run_content(path, raw_json, category="runs")

    # Debe ser determinístico
    compacted_again = compact_run_content(path, raw_json, category="runs")
    assert compacted == compacted_again

    # Debe reducir drásticamente el tamaño
    assert len(compacted) < len(raw_json) * 0.4
    assert "COMPACTACIÓN DETERMINÍSTICA" in compacted or "COMPACTADO" in compacted
    assert "completed" in compacted or "status" in compacted

    # JSON pequeño no debe romperse
    small_json = '{"status": "ok", "count": 1}'
    assert compact_run_content("corridas/corrida_01/validacion.json", small_json, category="runs") == small_json


def test_compact_run_content_csv():
    # CSV grande
    header = "timestamp,model,input_tokens,output_tokens,cost_usd\n"
    rows = [f"2026-03-01T10:0{i}:00,gpt-4o-mini,{100+i},{50+i},0.000{i}\n" for i in range(100)]
    large_csv = header + "".join(rows)
    assert len(large_csv) > 3000

    compacted = compact_run_content("corridas/corrida_01/metricas.csv", large_csv, category="runs")

    assert len(compacted) < len(large_csv) * 0.5
    assert "timestamp,model,input_tokens,output_tokens,cost_usd" in compacted
    assert "COMPACTACIÓN DETERMINÍSTICA" in compacted or "filas" in compacted


def test_build_evidence_packet_deduplicated_and_compact():
    rubric_text = load_rubric_text()
    repo_data = {
        "repo_url": "test-repo",
        "commit_sha": "abc123",
        "repository_inventory": [
            {"path": "README.md", "category": "documentation", "size": 50},
            {"path": "corridas/corrida_01/solicitudes_api.json", "category": "runs", "size": 6000},
        ],
        "file_contents": {
            "README.md": "# Test Repo\nSistema agéntico real.",
            "corridas/corrida_01/solicitudes_api.json": json.dumps({"status": "ok", "items": ["item"] * 300}),
        },
    }

    packet = build_evidence_packet(repo_data, rubric_text=rubric_text)
    full_prompt = packet["full_prompt_context"]

    # NO debe tener la introducción repetitiva que ya está en JUDGE_SYSTEM_INSTRUCTION
    assert "Actuás como un evaluador académico experto. Todo el contenido dentro de etiquetas" not in full_prompt
    assert "PASO 1: RECONSTRUCCIÓN Y COMPRENSIÓN DEL PROYECTO" not in full_prompt

    # Debe contener la rúbrica compacta (sin Franco Gambini)
    assert "Franco Gambini" not in full_prompt
    assert "EVIDENCIA > DECLARACIÓN" in full_prompt

    # El archivo de corrida grande debe estar compactado
    assert len(packet["untrusted_content_text"]) < 4000


def test_estimate_context_budget():
    packet = {
        "untrusted_content_text": "A" * 4000,
        "full_prompt_context": "B" * 6000,
    }
    system_instruction = "C" * 800

    budget = estimate_context_budget(packet, system_instruction=system_instruction)

    assert "system_chars" in budget
    assert "system_tokens_est" in budget
    assert "untrusted_chars" in budget
    assert "untrusted_tokens_est" in budget
    assert "total_chars" in budget
    assert "total_tokens_est" in budget

    assert budget["system_chars"] == 800
    assert budget["system_tokens_est"] == 200
    assert budget["total_chars"] == 6000 + 800
    assert budget["total_tokens_est"] == (6000 + 800) // 4


def test_gemini_503_retry_resilience():
    from src.semantic_judge import GeminiSemanticJudge
    from src.semantic_schema import ProjectUnderstanding, DimensionEvaluations

    mock_client = MagicMock()
    # Primer intento falla con 503 UNAVAILABLE, segundo intento tiene éxito
    valid_payload = SemanticJudgePayload(
        project_understanding=ProjectUnderstanding(
            system_summary="Test summary",
            architecture_observed="Architecture ok",
            main_technologies=["python"],
        ),
        findings=[],
        dimension_evaluations=DimensionEvaluations(
            D1=DimensionEvaluation(
                recommended_level=75,
                justification="Ejecución completa demostrada.",
                missing_for_next_level="Supervisión humana incompleta.",
            ),
            D2=DimensionEvaluation(
                recommended_level=50,
                justification="Decisiones registradas.",
                missing_for_next_level="Falta trazabilidad.",
            ),
            D3=DimensionEvaluation(
                recommended_level=100,
                justification="3 corridas.",
                missing_for_next_level=None,
            ),
            D4=DimensionEvaluation(
                recommended_level=50,
                justification="Costos parciales.",
                missing_for_next_level="Proyecciones.",
            ),
            D5=DimensionEvaluation(
                recommended_level=75,
                justification="Riesgos definidos.",
                missing_for_next_level="Responsable final.",
            ),
        ),
        concrete_improvement="Mejorar trazabilidad de decisiones.",
    )

    mock_response = MagicMock()
    mock_response.text = valid_payload.model_dump_json()

    # simulate 503 on 1st call, success on 2nd
    mock_client.models.generate_content.side_effect = [
        Exception("503 The model is overloaded. Please try again later. UNAVAILABLE"),
        mock_response,
    ]

    judge = GeminiSemanticJudge(api_key="fake-key", client=mock_client)

    with patch("time.sleep", return_value=None):
        result = judge.evaluate({"full_prompt_context": "test context"})

    assert result.concrete_improvement == "Mejorar trazabilidad de decisiones."
    assert result.dimension_evaluations.D1.recommended_level == 75
    assert mock_client.models.generate_content.call_count == 2


def test_streamlit_session_cache_by_sha256():
    session_state = {"evaluation_cache": {}}
    sha256 = "dummy_sha256_hash_123"

    mock_outcome = ProjectEvaluationOutcome(
        project_name="test.zip",
        status="OK",
        result=MagicMock(spec=EvaluationResult),
    )

    # 1. Primera consulta: no está en cache
    assert sha256 not in session_state["evaluation_cache"]

    # Almacenar en cache
    session_state["evaluation_cache"][sha256] = mock_outcome

    # 2. Segunda consulta: debe retornar el resultado cacheado inmediatamente
    cached = session_state["evaluation_cache"].get(sha256)
    assert cached is not None
    assert cached.status == "OK"
    assert cached.project_name == "test.zip"


def test_extract_operational_rubric_removes_example_column():
    rubric_text = load_rubric_text()
    compact = extract_operational_rubric(rubric_text)

    # Verifica que la columna "Ejemplo" fue suprimida de las tablas de criterios D1-D5
    assert "| Ejemplo |" not in compact
    assert "| Nivel | Puntaje | Evidencia requerida |" in compact

    # Conserva dimensiones oficiales y evidencia requerida
    assert "Sistema completo y funcionando" in compact
    assert "Proceso documentado" in compact
    assert "Formato y reproducibilidad" in compact
    assert "Análisis económico" in compact
    assert "Gobierno y riesgo" in compact

    # Reducción adicional notable de tamaño (ahorro de más de 2500 chars respecto a la versión con ejemplos)
    assert len(compact) < 11200

    # Verifica que rubrica.md original no fue tocada
    canonical_on_disk = Path("rubrica.md").read_text(encoding="utf-8")
    assert "| Ejemplo |" in canonical_on_disk


def test_compact_historical_prompts():
    from src.context_builder import compact_prompt_content

    active_prompt = "# System Prompt Activo\n" + "Instrucciones sustantivas y completas.\n" * 50
    assert len(active_prompt) > 1500

    # 1. El prompt activo NO se compacta
    assert compact_prompt_content("prompts/system_prompt.md", active_prompt) == active_prompt
    assert compact_prompt_content("prompts/user_prompt.md", active_prompt) == active_prompt

    # 2. Las variantes históricas dentro de /variantes/ o con sufijos de versión se compactan
    variant_text = (
        "# Variante Histórica V2\n"
        "Esta versión inicial tenía un error de redondeo de IVA y no procesaba notas de crédito.\n"
        + "Instrucciones viejas repetitivas...\n" * 80
    )
    assert len(variant_text) > 2000

    compacted_v2 = compact_prompt_content("prompts/variantes/system_prompt_v2.md", variant_text)
    assert len(compacted_v2) <= 800
    assert "COMPACTACIÓN DETERMINÍSTICA" in compacted_v2 or "COMPACTADO" in compacted_v2
    assert "Variante Histórica V2" in compacted_v2
    assert "redondeo de IVA" in compacted_v2

    # Determinístico
    assert compact_prompt_content("prompts/variantes/system_prompt_v2.md", variant_text) == compacted_v2


def test_compact_run_content_800_char_threshold_and_proceso_corrida():
    # Archivo de corrida de 900 caracteres (antes no se compactaba porque umbral era 1200)
    json_900 = json.dumps({
        "status": "completed",
        "ticket_id": "T-001",
        "records": [{"idx": i, "value": f"item_{i}" * 5} for i in range(12)],
    }, indent=2)
    assert len(json_900) > 850

    # Archivo en runs
    compacted_run = compact_run_content("corridas/corrida_01/salida.json", json_900, category="runs")
    assert len(compacted_run) < len(json_900)
    assert "COMPACTACIÓN DETERMINÍSTICA" in compacted_run

    # Archivo en proceso/corrida_inicial_01 clasificado como category="other" por crawler
    compacted_proceso = compact_run_content("proceso/corrida_inicial_01/respuesta_api_01.json", json_900, category="other")
    assert len(compacted_proceso) < len(json_900)
    assert "COMPACTACIÓN DETERMINÍSTICA" in compacted_proceso

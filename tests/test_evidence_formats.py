import sys
import types
import unittest


if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("La prueba unitaria no debe usar red")
    )
    sys.modules["requests"] = requests_stub


from src.evidence_extractor import extract_objective_evidence
from src.github_fetcher import classify_path


def evidence(contents):
    return extract_objective_evidence(
        {
            "repository_inventory": [
                classify_path(path, len(content.encode("utf-8")))
                for path, content in contents.items()
            ],
            "file_contents": contents,
        }
    )


class EvidenceFormatsTests(unittest.TestCase):
    def test_openai_import_alone_is_not_real_execution(self):
        ev = evidence({"src/agent.ts": 'import OpenAI from "openai";'})
        self.assertEqual(ev["system_type"], "rule_based_local")

    def test_openai_client_and_responses_call_are_real_execution(self):
        ev = evidence({
            "src/agent.ts": 'import OpenAI from "openai"; const client = new OpenAI(); await client.responses.create({input: "x"});'
        })
        self.assertEqual(ev["system_type"], "real_execution")
        self.assertTrue(any("SDK instanciado" in item for item in ev["found_real_execution"]))

    def test_openai_text_mention_is_not_real_execution(self):
        ev = evidence({"src/readme.ts": 'const note = "OpenAI Responses API";'})
        self.assertEqual(ev["system_type"], "rule_based_local")

    def test_dummy_behavior_is_preserved_with_sdk_code(self):
        ev = evidence({
            "src/agent.ts": 'const api = "API placeholder"; const client = new OpenAI(); await client.responses.create({});'
        })
        self.assertTrue(ev["has_dummy_connectors"])
        self.assertEqual(ev["system_type"], "partial_simulated_tool")

    def test_iteration_sections_with_substance_count_as_decisions(self):
        decisions = """# DECISIONES
## Iteración 1
Problema: el parser falla. Cambio: se agregó validación. Resultado: evita errores.
## Iteración 2
Contexto: salida incompleta. Corrección: se actualizó el contrato. Impacto: mejora trazabilidad.
## Iteración 3
Caso: fecha ausente. Cambio: se agregó metadata. Motivo: asegurar reproducibilidad.
"""
        self.assertEqual(evidence({"DECISIONES.md": decisions})["decision_count"], 3)

    def test_decision_table_rows_are_counted(self):
        decisions = """# DECISIONES
| Cambio | Motivo |
| --- | --- |
| Se agregó validación de esquema | Evita que salidas incompletas pasen como válidas. |
| Se corrigió el parser temporal | Permite reconstruir cada corrida sin ambigüedad. |
| Se incorporó auditoría de costos | Documenta el impacto económico del modelo. |
"""
        self.assertEqual(evidence({"DECISIONES.md": decisions})["decision_count"], 3)

    def test_table_summary_and_matching_section_are_deduplicated(self):
        decisions = """# DECISIONES
| Cambio | Motivo |
| --- | --- |
| Se agregó validación de esquema de salida | Evita aceptar salidas incompletas. |
## Iteración 1
Problema: se aceptaban salidas incompletas. Cambio: se agregó validación de esquema de salida. Impacto: evita aceptar salidas incompletas.
"""
        self.assertEqual(evidence({"DECISIONES.md": decisions})["decision_count"], 1)

    def test_similar_but_distinct_decisions_are_not_deduplicated(self):
        decisions = """# DECISIONES
| Cambio | Motivo |
| --- | --- |
| Se agregó validación de esquema de salida | Evita aceptar salidas incompletas. |
| Se agregó auditoría de costos por corrida | Permite revisar tarifas y proyecciones. |
"""
        self.assertEqual(evidence({"DECISIONES.md": decisions})["decision_count"], 2)

    def test_table_without_context_or_impact_is_not_a_decision(self):
        decisions = """# DECISIONES
| Cambio | Motivo |
| --- | --- |
| Actualizar README | |
"""
        self.assertEqual(evidence({"DECISIONES.md": decisions})["decision_count"], 0)

    def test_logs_without_change_and_impact_do_not_count_as_decisions(self):
        decisions = """# DECISIONES
## Iteración 1
Se ejecutó el proceso a las 10:00.
"""
        self.assertEqual(evidence({"DECISIONES.md": decisions})["decision_count"], 0)

    def test_named_run_files_form_three_complete_triads(self):
        contents = {"README.md": "x", "DECISIONES.md": "x", "prompts/system.md": "instrucciones " * 10}
        for run in ("a", "b", "c"):
            contents[f"corridas/{run}/entrada.md"] = "Fecha de ejecución: 2026-01-01"
            contents[f"corridas/{run}/salida.json"] = "{}"
            contents[f"corridas/{run}/metadata.json"] = "Fecha: 2026-01-01"
        ev = evidence(contents)
        self.assertEqual(ev["corrida_count"], 3)
        self.assertTrue(ev["has_complete_triad"])

    def test_raw_output_metadata_and_input_reference_form_triads(self):
        contents = {"README.md": "x", "DECISIONES.md": "x", "prompts/system.md": "instrucciones " * 10}
        for number in ("001", "002", "003"):
            contents[f"prompts/casos/solicitud_{number}.md"] = "entrada"
            contents[f"corridas/raw/solicitud_{number}_modelo_20260101.md"] = (
                f"Caso: solicitud_{number}.md\nFecha: 2026-01-01T10:00:00\n\nSalida completa del agente. " * 10
            )
        ev = evidence(contents)
        self.assertGreaterEqual(ev["corrida_count"], 3)
        self.assertTrue(ev["has_complete_triad"])

    def test_global_input_output_and_date_do_not_form_a_triad(self):
        contents = {
            "corridas/a/entrada.md": "entrada",
            "corridas/b/salida.json": "{}",
            "corridas/c/metadata.json": "Fecha: 2026-01-01",
        }
        self.assertFalse(evidence(contents)["has_complete_triad"])

    def test_failed_run_with_input_output_and_date_is_complete(self):
        contents = {}
        for run in ("a", "b", "c"):
            contents[f"corridas/{run}/entrada.md"] = "Fecha de ejecución: 2026-01-01"
            contents[f"corridas/{run}/salida.json"] = '{"estado":"error"}'
        self.assertTrue(evidence(contents)["has_complete_triad"])

    def test_token_labels_and_tables_are_measurements(self):
        labeled = evidence({"README.md": "Modelo: x\nCosto por corrida: USD 0.01\nTokens de entrada: 4544\nTokens de salida: 800"})
        table = evidence({"README.md": "| Modelo | Tokens in | Tokens out | Costo USD |\n| --- | --- | --- | --- |\n| x | 4544 | 800 | 0.01 |"})
        self.assertTrue(labeled["econ"]["has_tokens_num"])
        self.assertTrue(table["econ"]["has_tokens_num"])

    def test_token_word_without_a_measurement_is_not_enough(self):
        ev = evidence({"README.md": "Los tokens se medirán en una etapa futura."})
        self.assertFalse(ev["econ"]["has_tokens_num"])

    def test_empty_token_table_and_unrelated_numbers_are_not_measurements(self):
        empty = evidence({"README.md": "| Modelo | Tokens in | Costo USD |\n| --- | --- | --- |\n| x |  | 0.01 |"})
        unrelated = evidence({"README.md": "El servidor tiene 32 GB y los tokens son importantes."})
        self.assertFalse(empty["econ"]["has_tokens_num"])
        self.assertFalse(unrelated["econ"]["has_tokens_num"])

    def test_server_cost_without_ai_context_is_not_economic_cost_evidence(self):
        ev = evidence({"README.md": "Costo del servidor: USD 120 por mes."})
        self.assertFalse(ev["econ"]["has_cost_num"])


if __name__ == "__main__":
    unittest.main()

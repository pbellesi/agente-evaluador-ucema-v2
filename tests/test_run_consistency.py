import sys
import types
import unittest


if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("La prueba unitaria no debe usar red")
    )
    sys.modules["requests"] = requests_stub


from src.deterministic_evaluator import evaluate_repository_deterministically
from src.evidence_extractor import extract_objective_evidence
from src.github_fetcher import classify_path


def evidence(contents):
    return extract_objective_evidence({
        "repository_inventory": [
            classify_path(path, len(content.encode("utf-8")))
            for path, content in contents.items()
        ],
        "file_contents": contents,
    })


def evaluate(contents):
    return evaluate_repository_deterministically({
        "repository": "synthetic/run-consistency",
        "evaluated_revision": "synthetic@fixed",
        "repository_inventory": [
            classify_path(path, len(content.encode("utf-8")))
            for path, content in contents.items()
        ],
        "file_contents": contents,
    })


def base_structure():
    return {
        "README.md": "Proyecto sintético.",
        "DECISIONES.md": "# DECISIONES\nRegistro inspeccionable.",
        "prompts/system_prompt.md": "Rol del agente. Instrucciones para procesar una solicitud concreta. " * 3,
        "prompts/user_prompt.md": "Usuario: procesar la solicitud con salida JSON. " * 3,
        "src/agent.ts": 'const client = new OpenAI(); await client.responses.create({input: "x"});',
    }


def add_run(contents, name, request_id, output_id, amount=None, review=None):
    payload = {"request_id": request_id}
    if amount is not None:
        payload["amount"] = amount
    output = {"request_id": output_id, "result": "processed"}
    if review is not None:
        output["human_review_required"] = review
    import json
    contents[f"corridas/{name}/input.json"] = json.dumps(payload)
    contents[f"corridas/{name}/output.json"] = json.dumps(output)
    contents[f"corridas/{name}/metadata.json"] = '{"startedAt":"2026-01-01T10:00:00Z"}'


class RunConsistencyTests(unittest.TestCase):
    def test_comments_and_string_literals_do_not_prove_sdk_execution(self):
        ev = evidence({
            "src/agent.ts": '''
                // const client = new OpenAI(); await client.responses.create({});
                const example = "client.responses.create({})";
                /* const client = new OpenAI(); await client.responses.create({}); */
                value = 1 # fetch("https://example.test")
            ''',
        })
        self.assertEqual(ev["system_type"], "rule_based_local")

    def test_mismatched_identifiers_in_a_run_invalidate_its_complete_trace(self):
        contents = base_structure()
        add_run(contents, "one", "request-one", "request-other")
        ev = evidence(contents)
        self.assertEqual(ev["complete_trace_count"], 0)
        self.assertEqual(ev["run_input_output_inconsistency_count"], 1)
        self.assertTrue(ev["contradictions"])

    def test_camel_case_identifiers_are_compared(self):
        contents = base_structure()
        contents["corridas/one/input.json"] = '{"requestId":"request-one"}'
        contents["corridas/one/output.json"] = '{"requestId":"request-other"}'
        contents["corridas/one/metadata.json"] = '{"startedAt":"2026-01-01T10:00:00Z"}'
        self.assertEqual(evidence(contents)["run_input_output_inconsistency_count"], 1)

    def test_reused_output_identifier_across_distinct_inputs_is_detected(self):
        contents = base_structure()
        add_run(contents, "one", "request-one", "shared-output")
        add_run(contents, "two", "request-two", "shared-output")
        ev = evidence(contents)
        self.assertGreaterEqual(ev["reused_incompatible_output_count"], 2)

    def test_inconsistent_structured_runs_do_not_receive_full_d1_or_d3_credit(self):
        contents = base_structure()
        for name, request_id in (("one", "request-one"), ("two", "request-two"), ("three", "request-three")):
            add_run(contents, name, request_id, "shared-output")
        result = evaluate(contents)
        self.assertEqual(result.dimensions[0].level_percent, 50)
        self.assertEqual(result.dimensions[2].level_percent, 75)
        self.assertTrue(result.integrity_notes)

    def test_documented_review_threshold_contradicted_by_run_caps_d5(self):
        contents = base_structure()
        contents["docs/gobierno_riesgo.md"] = (
            "El agente tiene acceso de solo lectura mediante permiso restringido. "
            "Si ocurre una falla puede afectar resultados; respuesta: bloquear y notificar. "
            "Un importe superior a 100 requiere revisión humana antes de publicar. "
            "Responsable final con firma: analista."
        )
        for name, request_id in (("one", "request-one"), ("two", "request-two"), ("three", "request-three")):
            add_run(contents, name, request_id, request_id, amount=200, review=False)
        result = evaluate(contents)
        self.assertEqual(result.dimensions[4].level_percent, 50)
        self.assertTrue(any("gobierno" in note.lower() for note in result.integrity_notes))


if __name__ == "__main__":
    unittest.main()

import sys
import types
import unittest

# Las pruebas de planificación no usan red. El runtime empaquetado de esta
# sesión no incluye requests, aunque producción lo declara en requirements.txt.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("La prueba unitaria no debe usar red"))
    sys.modules["requests"] = requests_stub

from src.evidence_extractor import extract_objective_evidence
from src.github_fetcher import TRUNCATION_MARKER, build_retrieval_plan, classify_path


def record(path, size=1024):
    return classify_path(path, size)


class RetrievalCoverageTests(unittest.TestCase):
    def test_typescript_and_tsx_are_implementation(self):
        self.assertEqual(classify_path("src/agent.ts")["category"], "implementation")
        self.assertEqual(classify_path("src/App.tsx")["category"], "implementation")
        self.assertIn("code", classify_path("src/App.tsx")["labels"])

    def test_economics_and_governance_labels_are_path_based(self):
        self.assertIn("economics", classify_path("docs/token_budget.md")["labels"])
        labels = classify_path("docs/gobierno_y_riesgos.md")["labels"]
        self.assertIn("governance", labels)
        self.assertIn("risk", labels)

    def test_critical_coverage_precedes_many_large_runs(self):
        inventory = [
            record("README.md", 2000), record("DECISIONES.md", 2000),
            record("agente/run.ts", 4000), record("src/services/Client.ts", 4000),
            record("prompts/system.md", 2000), record("tests/test_agent.ts", 4000),
            record("docs/analisis_economico.md", 2000), record("docs/gobierno_y_riesgos.md", 2000),
        ]
        inventory.extend(record(f"corridas/{index:03d}/run.json", 200000) for index in range(120))
        plan = build_retrieval_plan(inventory)
        paths = {item["path"] for item in plan["selected"]}
        self.assertIn("agente/run.ts", paths)
        self.assertIn("docs/analisis_economico.md", paths)
        self.assertIn("docs/gobierno_y_riesgos.md", paths)
        self.assertIn("prompts/system.md", paths)
        self.assertIn("tests/test_agent.ts", paths)

    def test_structure_prefers_readme_and_decisions(self):
        inventory = [
            record("README.md", 1000), record("DECISIONES.md", 1000),
            record("AGENTS.md", 1000), record("ESTADO_PROYECTO.md", 1000),
            record("agente/README.md", 1000), record("docs/README.md", 1000),
        ]
        plan = build_retrieval_plan(inventory, {"phase1_min_files": {"structure": 2}})
        phase1 = {item["path"] for item in plan["selected"] if item["selection_phase"] == "phase1"}
        self.assertIn("README.md", phase1)
        self.assertIn("DECISIONES.md", phase1)
        self.assertNotIn("agente/README.md", phase1)

    def test_run_truncation_and_directory_budget_are_bounded(self):
        inventory = [record("corridas/001/run.json", 200000)]
        plan = build_retrieval_plan(inventory, {"total_budget_bytes": 100000})
        selected = plan["selected"][0]
        self.assertLessEqual(selected["byte_limit"], 24 * 1024)
        self.assertGreaterEqual(selected["byte_limit"], len(TRUNCATION_MARKER))

    def test_selection_is_stable(self):
        inventory = [
            record("docs/costos.md", 2000), record("docs/economia.md", 2000),
            record("src/main.ts", 3000), record("prompts/system.md", 1000),
            record("corridas/a/input.json", 1000), record("tests/test_main.ts", 1000),
        ]
        first = build_retrieval_plan(inventory)
        second = build_retrieval_plan(list(reversed(inventory)))
        self.assertEqual(first["selected"], second["selected"])
        self.assertEqual(first["skipped"], second["skipped"])

    def test_skipped_document_is_not_absent(self):
        inventory = [record("README.md", 1000), record("docs/analisis_economico.md", 2000)]
        evidence = extract_objective_evidence({"repository_inventory": inventory, "file_contents": {"README.md": "Proyecto"}})
        self.assertEqual(evidence["coverage"]["economics"]["status"], "skipped")
        self.assertFalse(evidence["econ"]["has_tokens_num"])

    def test_multiple_economic_documents_have_stable_sources(self):
        inventory = [record("docs/costos.md", 1000), record("docs/economia.md", 1000)]
        contents = {
            "docs/costos.md": "100 tokens USD 0 proyección anual modelo adecuado",
            "docs/economia.md": "200 tokens USD 0 proyección anual modelo adecuado",
        }
        evidence = extract_objective_evidence({"repository_inventory": inventory, "file_contents": contents})
        self.assertEqual(evidence["evidence_sources"]["economics"], ["docs/costos.md", "docs/economia.md"])
        self.assertTrue(evidence["econ"]["has_tokens_num"])

    def test_markdown_and_styles_are_not_code_only_by_folder(self):
        inventory = [record("agente/README.md", 100), record("src/styles.css", 100)]
        evidence = extract_objective_evidence({"repository_inventory": inventory, "file_contents": {"agente/README.md": "texto", "src/styles.css": "body {}"}})
        self.assertFalse(evidence["has_code"])


if __name__ == "__main__":
    unittest.main()

import unittest
from src.context_builder import build_evidence_packet


class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.sample_repo_data = {
            "repo_url": "usuario/agente-prueba",
            "branch": "main",
            "commit_sha": "abc12345",
            "repository_inventory": [
                {"path": "README.md", "category": "documentation", "size": 150},
                {"path": "DECISIONES.md", "category": "documentation", "size": 200},
                {"path": "prompts/system_prompt.md", "category": "prompts", "size": 180},
                {"path": "src/main.py", "category": "implementation", "size": 350},
                {"path": "corridas/corrida_01/salida.json", "category": "runs", "size": 120},
                {"path": "tests/test_main.py", "category": "tests", "size": 250},
                {"path": "assets/logo.png", "category": "other", "size": 1024},
            ],
            "file_contents": {
                "README.md": "# Agente de Prueba\nSistema que atiende consultas.",
                "DECISIONES.md": "# Decisiones\nSe optó por arquitectura modular.",
                "prompts/system_prompt.md": "Sos un asistente útil de clasificación.",
                "src/main.py": "def main():\n    print('ejecutando agente')",
                "corridas/corrida_01/salida.json": "{\"status\": \"ok\", \"resultado\": 42}",
                "tests/test_main.py": "def test_main(): assert True",
            },
        }

    def test_full_inventory_preserved(self):
        packet = build_evidence_packet(self.sample_repo_data)
        self.assertIn("inventory", packet)
        self.assertEqual(len(packet["inventory"]), 7)
        paths = [item["path"] for item in packet["inventory"]]
        self.assertIn("assets/logo.png", paths)
        self.assertIn("README.md", paths)

    def test_untrusted_data_delimiters_present(self):
        packet = build_evidence_packet(self.sample_repo_data)
        prompt_context = packet["full_prompt_context"]
        self.assertIn('<untrusted_repo_content path="README.md">', prompt_context)
        self.assertIn('</untrusted_repo_content>', prompt_context)
        self.assertIn('<untrusted_repo_content path="src/main.py">', prompt_context)

    def test_explicit_truncation_marker(self):
        large_content = "X" * 5000
        repo_data_large = dict(self.sample_repo_data)
        repo_data_large["file_contents"] = dict(self.sample_repo_data["file_contents"])
        repo_data_large["file_contents"]["README.md"] = large_content

        packet = build_evidence_packet(repo_data_large, max_file_chars=1000)
        prompt_context = packet["full_prompt_context"]
        self.assertIn("[TRUNCADO POR TAMAÑO:", prompt_context)

    def test_rubric_positioned_at_end_as_evaluation_framework(self):
        rubric_sample = "RUBRICA OFICIAL D1 A D5"
        packet = build_evidence_packet(self.sample_repo_data, rubric_text=rubric_sample)
        prompt_context = packet["full_prompt_context"]

        pos_repo_content = prompt_context.find('<untrusted_repo_content path="src/main.py">')
        pos_rubric = prompt_context.find(rubric_sample)

        self.assertNotEqual(pos_repo_content, -1)
        self.assertNotEqual(pos_rubric, -1)
        # La rúbrica debe ubicarse DESPUÉS de la evidencia para favorecer primero entender el trabajo
        self.assertGreater(pos_rubric, pos_repo_content)

    def test_empty_or_minimal_repo_data(self):
        empty_data = {"repo_url": "test/empty"}
        packet = build_evidence_packet(empty_data)
        self.assertEqual(packet["repository_name"], "test/empty")
        self.assertEqual(packet["inventory"], [])
        self.assertIn("full_prompt_context", packet)


if __name__ == "__main__":
    unittest.main()

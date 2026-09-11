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


def has_dummy(content: str) -> bool:
    path = "src/example.tsx"
    evidence = extract_objective_evidence(
        {
            "repository_inventory": [classify_path(path, len(content))],
            "file_contents": {path: content},
        }
    )
    return evidence["has_dummy_connectors"]


class PlaceholderFalsePositiveTests(unittest.TestCase):
    def test_ui_input_placeholder_is_not_dummy(self):
        self.assertFalse(has_dummy('<input placeholder="Buscar video" />'))

    def test_ui_placeholder_with_api_like_example_is_not_dummy(self):
        self.assertFalse(
            has_dummy('<input placeholder="checkout-api, payments-db" />')
        )

    def test_ui_placeholder_with_api_word_is_not_dummy(self):
        self.assertFalse(has_dummy('<input placeholder="Ingresá tu API" />'))

    def test_ui_placeholder_variable_is_not_dummy(self):
        self.assertFalse(has_dummy('const placeholder = "Buscar"'))

    def test_ui_placeholder_identifier_is_not_dummy(self):
        self.assertFalse(has_dummy('const LibraryPlaceholder = () => null'))

    def test_placeholder_connector_is_dummy(self):
        self.assertTrue(has_dummy('const connector = "placeholder connector"'))

    def test_api_placeholder_is_dummy(self):
        self.assertTrue(has_dummy('const api = "API placeholder"'))

    def test_api_placeholder_with_following_text_is_dummy(self):
        self.assertTrue(
            has_dummy('const api = "API placeholder pendiente de implementar"')
        )

    def test_integration_placeholder_is_dummy(self):
        self.assertTrue(has_dummy('const integration = "integración usada como placeholder"'))

    def test_integration_placeholder_is_dummy_without_intermediate_words(self):
        self.assertTrue(has_dummy('const integration = "integración placeholder"'))

    def test_placeholder_connector_reverse_order_is_dummy(self):
        self.assertTrue(has_dummy('const connector = "placeholder de conector"'))


if __name__ == "__main__":
    unittest.main()

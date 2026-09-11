import io
import os
import sys
import types
import unittest
import zipfile
from unittest.mock import patch
from urllib.parse import unquote

# Las pruebas reemplazan requests por un fake local y no deben usar red.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("La prueba unitaria no debe usar red")
    )
    sys.modules["requests"] = requests_stub

from src.evaluator_engine import (
    PRIMARY_RATE_LIMIT_MARKER,
    evaluate_with_rate_limit_guard,
    rate_limit_access_error_result,
    run_evaluation,
)
from src.github_fetcher import _github_headers, classify_github_error, fetch_repository_data, parse_github_url
from src.schema import EvaluationResult


class FakeResponse:
    def __init__(self, status_code, payload=None, content=b"", headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.headers = headers or {}

    def json(self):
        return self._payload


def archive_bytes():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        archive.writestr("fixture-root/README.md", "# Repositorio sintético\n")
    return payload.getvalue()


class FakeGitHub:
    def __init__(self, default_branch, references):
        self.default_branch = default_branch
        self.references = references
        self.calls = []
        self.request_headers = []
        self.archive = archive_bytes()

    def get(self, url, timeout, headers=None):
        self.calls.append(url)
        self.request_headers.append(headers or {})
        base = "https://api.github.com/repos/acme/demo"
        if url == base:
            return FakeResponse(200, {"default_branch": self.default_branch})
        if url.startswith(f"{base}/commits/"):
            reference = unquote(url.rsplit("/", 1)[-1])
            sha = self.references.get(reference)
            return FakeResponse(200, {"sha": sha}) if sha else FakeResponse(404)
        if url.startswith(f"{base}/zipball/"):
            return FakeResponse(200, content=self.archive)
        return FakeResponse(404)


class GitHubReferenceResolutionTests(unittest.TestCase):
    def fetch_with(self, url, default_branch="main", references=None):
        references = references or {default_branch: "a" * 40}
        github = FakeGitHub(default_branch, references)
        with patch("src.github_fetcher.requests.get", side_effect=github.get):
            data = fetch_repository_data(url)
        return data, github.calls

    def test_simple_url_uses_default_main_branch(self):
        data, calls = self.fetch_with("https://github.com/acme/demo", "main")
        self.assertEqual(data["branch"], "main")
        self.assertEqual(data["evaluated_revision"], "a" * 40)
        self.assertIn("https://api.github.com/repos/acme/demo", calls)

    def test_simple_url_uses_non_main_default_branch(self):
        data, calls = self.fetch_with(
            "https://github.com/acme/demo",
            "trunk",
            {"trunk": "b" * 40},
        )
        self.assertEqual(data["branch"], "trunk")
        self.assertEqual(data["evaluated_revision"], "b" * 40)
        self.assertIn("https://api.github.com/repos/acme/demo/commits/trunk", calls)
        self.assertNotIn("https://api.github.com/repos/acme/demo/commits/main", calls)

    def test_explicit_sha_is_respected_without_metadata_lookup(self):
        sha = "c" * 40
        data, calls = self.fetch_with(
            f"https://github.com/acme/demo/commit/{sha}",
            "trunk",
            {sha: sha},
        )
        self.assertEqual(data["branch"], sha)
        self.assertEqual(data["evaluated_revision"], sha)
        self.assertNotIn("https://api.github.com/repos/acme/demo", calls)

    def test_explicit_branch_is_respected_without_metadata_lookup(self):
        data, calls = self.fetch_with(
            "https://github.com/acme/demo/tree/release",
            "trunk",
            {"release": "d" * 40},
        )
        self.assertEqual(data["branch"], "release")
        self.assertNotIn("https://api.github.com/repos/acme/demo", calls)

    def test_explicit_tag_is_respected_without_metadata_lookup(self):
        data, calls = self.fetch_with(
            "https://github.com/acme/demo/tree/v1.2.0",
            "trunk",
            {"v1.2.0": "e" * 40},
        )
        self.assertEqual(data["branch"], "v1.2.0")
        self.assertNotIn("https://api.github.com/repos/acme/demo", calls)

    def test_nonexistent_explicit_reference_reports_the_attempted_reference(self):
        github = FakeGitHub("trunk", {"trunk": "f" * 40})
        with patch("src.github_fetcher.requests.get", side_effect=github.get):
            with self.assertRaisesRegex(RuntimeError, "referencia 'missing'"):
                fetch_repository_data("https://github.com/acme/demo/tree/missing")

    def test_access_error_for_one_repository_does_not_poison_the_next_evaluation(self):
        successful_data = {
            "repository": "acme/ok",
            "evaluated_revision": "g" * 40,
            "repository_inventory": [],
            "file_contents": {},
        }
        completed = EvaluationResult(
            repository="acme/ok",
            evaluated_revision="g" * 40,
            evaluation_date="2026-09-06",
            evaluation_status="completed",
            dimensions=[],
            final_score=0,
            concrete_improvement="",
            integrity_notes=[],
        )
        with patch(
            "src.evaluator_engine.fetch_repository_data",
            side_effect=[RuntimeError("referencia inexistente"), successful_data],
        ), patch("src.evaluator_engine.evaluate_repository_deterministically", return_value=completed):
            failed = run_evaluation("https://github.com/acme/missing")
            succeeded = run_evaluation("https://github.com/acme/ok")
        self.assertEqual(failed.evaluation_status, "access_error")
        self.assertEqual(succeeded.evaluation_status, "completed")


class GitHubHttpClientTests(unittest.TestCase):
    def test_anonymous_request_has_user_agent_without_authorization(self):
        github = FakeGitHub("main", {"main": "a" * 40})
        with patch("src.github_fetcher._github_token", return_value=None), patch(
            "src.github_fetcher.requests.get", side_effect=github.get
        ):
            fetch_repository_data("https://github.com/acme/demo")
        self.assertTrue(all(headers["User-Agent"] == "agente-evaluador-ucema" for headers in github.request_headers))
        self.assertTrue(all("Authorization" not in headers for headers in github.request_headers))

    def test_token_adds_bearer_authorization_header(self):
        github = FakeGitHub("main", {"main": "a" * 40})
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}), patch(
            "src.github_fetcher.requests.get", side_effect=github.get
        ):
            fetch_repository_data("https://github.com/acme/demo")
        self.assertTrue(all(headers.get("Authorization") == "Bearer test-token" for headers in github.request_headers))

    def test_streamlit_secret_is_used_when_environment_token_is_absent(self):
        fake_streamlit = types.SimpleNamespace(secrets={"GITHUB_TOKEN": "secret-from-streamlit"})
        with patch.dict(os.environ, {"GITHUB_TOKEN": ""}), patch.dict(
            sys.modules, {"streamlit": fake_streamlit}
        ):
            headers = _github_headers()
        self.assertEqual(headers.get("Authorization"), "Bearer secret-from-streamlit")

    def test_token_never_appears_in_access_error(self):
        token = "secret-token-never-visible"
        response = FakeResponse(
            403,
            {"message": "API rate limit exceeded"},
            headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1788705053"},
        )
        with patch.dict(os.environ, {"GITHUB_TOKEN": token}), patch(
            "src.github_fetcher.requests.get", return_value=response
        ):
            result = run_evaluation("https://github.com/acme/demo")
        self.assertEqual(result.evaluation_status, "access_error")
        self.assertNotIn(token, result.concrete_improvement)
        self.assertNotIn(token, " ".join(result.integrity_notes))

    def test_primary_rate_limit_is_classified_from_remaining_zero(self):
        details = classify_github_error(FakeResponse(403, headers={"X-RateLimit-Remaining": "0"}))
        self.assertEqual(details["category"], "PRIMARY_RATE_LIMIT")

    def test_secondary_rate_limit_is_classified_from_retry_after_or_message(self):
        retry_details = classify_github_error(FakeResponse(429, headers={"Retry-After": "30"}))
        message_details = classify_github_error(
            FakeResponse(403, {"message": "You have exceeded a secondary rate limit."})
        )
        self.assertEqual(retry_details["category"], "SECONDARY_RATE_LIMIT")
        self.assertEqual(message_details["category"], "SECONDARY_RATE_LIMIT")

    def test_forbidden_and_not_found_are_classified_without_rate_limit_signals(self):
        forbidden = classify_github_error(FakeResponse(403, {"message": "Resource not accessible"}))
        missing = classify_github_error(FakeResponse(404, {"message": "Not Found"}))
        self.assertEqual(forbidden["category"], "FORBIDDEN_OTHER")
        self.assertEqual(missing["category"], "NOT_FOUND")

    def test_batch_guard_stops_evaluations_after_primary_rate_limit(self):
        primary = rate_limit_access_error_result("https://github.com/acme/limited")
        with patch("src.evaluator_engine.run_evaluation", return_value=primary) as runner:
            first, blocked = evaluate_with_rate_limit_guard("https://github.com/acme/limited", False)
            second, still_blocked = evaluate_with_rate_limit_guard("https://github.com/acme/not-requested", blocked)
        self.assertTrue(blocked)
        self.assertTrue(still_blocked)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(first.evaluation_status, "access_error")
        self.assertTrue(second.integrity_notes[0].startswith(PRIMARY_RATE_LIMIT_MARKER))


class ParseGitHubUrlTests(unittest.TestCase):
    def test_simple_url_has_no_explicit_reference(self):
        _, _, revision, _ = parse_github_url("https://github.com/acme/demo")
        self.assertIsNone(revision)


if __name__ == "__main__":
    unittest.main()

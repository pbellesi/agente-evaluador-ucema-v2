import unittest

from src.batch_summary import summarize_batch_results
from src.schema import DimensionResult, EvaluationResult


DIMENSION_NAMES = [
    "Sistema",
    "Proceso",
    "Reproducibilidad",
    "Economía",
    "Gobierno",
]


def completed_result(repository, score, levels=(100, 75, 50, 25, 0)):
    dimensions = [
        DimensionResult(
            dimension=name,
            weight=20,
            level_percent=level,
            score=level / 5,
            justification="Fixture sintético.",
        )
        for name, level in zip(DIMENSION_NAMES, levels)
    ]
    return EvaluationResult(
        repository=repository,
        evaluated_revision="a" * 40,
        evaluation_date="2026-09-06",
        evaluation_status="completed",
        dimensions=dimensions,
        final_score=score,
        concrete_improvement="",
        integrity_notes=[],
    )


def access_error_result(repository):
    return EvaluationResult(
        repository=repository,
        evaluated_revision="unknown",
        evaluation_date="2026-09-06",
        evaluation_status="access_error",
        dimensions=[],
        final_score=None,
        concrete_improvement="No disponible.",
        integrity_notes=["Error de acceso."],
    )


class BatchSummaryTests(unittest.TestCase):
    def test_calculates_mean_median_approvals_and_dimension_averages(self):
        summary = summarize_batch_results(
            [
                completed_result("acme/a", 50, (100, 75, 50, 25, 0)),
                completed_result("acme/b", 70, (50, 75, 100, 25, 50)),
                completed_result("acme/c", 90, (100, 25, 50, 75, 100)),
            ],
            approval_threshold=60,
        )

        self.assertEqual(summary["processed_count"], 3)
        self.assertEqual(summary["valid_count"], 3)
        self.assertEqual(summary["access_error_count"], 0)
        self.assertEqual(summary["mean_score"], 70.0)
        self.assertEqual(summary["median_score"], 70.0)
        self.assertEqual(summary["approved_count"], 2)
        self.assertEqual(summary["approval_rate"], 2 / 3)
        self.assertEqual(summary["dimension_averages"], [250 / 3, 175 / 3, 200 / 3, 125 / 3, 150 / 3])

    def test_excludes_access_errors_from_academic_statistics(self):
        summary = summarize_batch_results(
            [completed_result("acme/ok", 80), access_error_result("acme/error")],
            approval_threshold=60,
        )

        self.assertEqual(summary["processed_count"], 2)
        self.assertEqual(summary["valid_count"], 1)
        self.assertEqual(summary["access_error_count"], 1)
        self.assertEqual(summary["mean_score"], 80.0)
        self.assertEqual(summary["median_score"], 80.0)
        self.assertEqual(summary["approved_count"], 1)
        self.assertEqual(summary["approval_rate"], 1.0)

    def test_empty_batch_has_no_academic_statistics(self):
        summary = summarize_batch_results([], approval_threshold=60)

        self.assertEqual(summary["processed_count"], 0)
        self.assertEqual(summary["valid_count"], 0)
        self.assertEqual(summary["access_error_count"], 0)
        self.assertIsNone(summary["mean_score"])
        self.assertIsNone(summary["median_score"])
        self.assertIsNone(summary["approval_rate"])
        self.assertEqual(summary["dimension_averages"], [None] * 5)

    def test_single_valid_result_and_all_access_errors_are_handled(self):
        one_valid = summarize_batch_results([completed_result("acme/one", 65)], approval_threshold=60)
        all_errors = summarize_batch_results(
            [access_error_result("acme/a"), access_error_result("acme/b")], approval_threshold=60
        )

        self.assertEqual(one_valid["mean_score"], 65.0)
        self.assertEqual(one_valid["median_score"], 65.0)
        self.assertEqual(one_valid["approved_count"], 1)
        self.assertEqual(all_errors["processed_count"], 2)
        self.assertEqual(all_errors["valid_count"], 0)
        self.assertEqual(all_errors["access_error_count"], 2)
        self.assertIsNone(all_errors["mean_score"])
        self.assertIsNone(all_errors["approval_rate"])

    def test_threshold_only_changes_visual_classification(self):
        result = completed_result("acme/threshold", 60)
        lower = summarize_batch_results([result], approval_threshold=60)
        higher = summarize_batch_results([result], approval_threshold=61)

        self.assertEqual(lower["approved_count"], 1)
        self.assertEqual(higher["approved_count"], 0)
        self.assertEqual(result.final_score, 60)
        self.assertEqual(result.dimensions[0].level_percent, 100)

    def test_all_or_no_results_can_be_approved_and_equal_scores_keep_their_median(self):
        results = [completed_result("acme/a", 70), completed_result("acme/b", 70)]
        all_approved = summarize_batch_results(results, approval_threshold=70)
        none_approved = summarize_batch_results(results, approval_threshold=71)

        self.assertEqual(all_approved["approved_count"], 2)
        self.assertEqual(all_approved["approval_rate"], 1.0)
        self.assertEqual(all_approved["median_score"], 70.0)
        self.assertEqual(none_approved["approved_count"], 0)
        self.assertEqual(none_approved["approval_rate"], 0.0)

    def test_missing_or_invalid_dimension_levels_do_not_break_summary(self):
        result = completed_result("acme/partial", 75)
        result.dimensions[1].level_percent = None
        result.dimensions = result.dimensions[:3]

        summary = summarize_batch_results([result], approval_threshold=60)

        self.assertEqual(summary["dimension_averages"], [100.0, None, 50.0, None, None])


if __name__ == "__main__":
    unittest.main()

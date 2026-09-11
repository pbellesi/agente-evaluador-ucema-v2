"""
CLI oficial del Agente Evaluador UCEMA V2 (Juez Semántico).
Ejecuta la evaluación interpretativa mediante LLM con control determinístico de contrato y pesos.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.context_builder import build_evidence_packet
from src.evaluation_validator import validate_and_score_evaluation
from src.github_fetcher import GitHubRequestError, fetch_repository_data
from src.schema import EvaluationResult
from src.semantic_judge import (
    GeminiSemanticJudge,
    SemanticJudgeConfigError,
    SemanticJudgeEvaluationError,
)
from src.zip_repository import ZipRepositoryError, build_repository_data_from_zip


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Agente Evaluador UCEMA V2: Evaluación semántica de proyectos mediante LLM y runtime determinístico.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--github", metavar="URL", help="URL pública del repositorio objetivo en GitHub.")
    source.add_argument("--zip", dest="zip_path", metavar="PATH", help="Ruta del archivo ZIP del proyecto.")
    parser.add_argument(
        "--model",
        dest="model_name",
        default=None,
        help="Modelo de Gemini a utilizar (default: gemini-3.7-flash o variable GEMINI_MODEL).",
    )
    return parser


def _load_rubric_text() -> Optional[str]:
    rubric_path = PROJECT_ROOT / "rubrica.md"
    if rubric_path.is_file():
        try:
            return rubric_path.read_text(encoding="utf-8")
        except Exception:
            return None
    return None


def run_evaluation_v2(
    zip_path: Optional[str] = None,
    github_url: Optional[str] = None,
    model_name: Optional[str] = None,
) -> EvaluationResult:
    """
    Ejecuta el pipeline completo V2:
    1. Ingesta segura existente (ZIP o GitHub)
    2. ContextBuilder (organización y delimitación de contexto)
    3. GeminiSemanticJudge (análisis interpretativo estructurado)
    4. EvaluationValidator (verificación de citas, niveles estrictos y pesos oficiales)
    """
    # 1. Ingesta segura
    if zip_path:
        path_obj = Path(zip_path)
        if not path_obj.is_file():
            raise FileNotFoundError(f"No se encontró el archivo ZIP en: {zip_path}")
        zip_bytes = path_obj.read_bytes()
        repo_data = build_repository_data_from_zip(zip_bytes, path_obj.name)
    elif github_url:
        repo_data = fetch_repository_data(github_url)
    else:
        raise ValueError("Debe proporcionarse --zip o --github.")

    # 2. Construcción de Contexto
    rubric_text = _load_rubric_text()
    evidence_packet = build_evidence_packet(repo_data, rubric_text=rubric_text)

    # 3. Juez Semántico
    judge = GeminiSemanticJudge(model_name=model_name)
    payload = judge.evaluate(evidence_packet)

    # 4. Validación determinística y scoring matemático
    return validate_and_score_evaluation(payload, repo_data)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    try:
        result = run_evaluation_v2(
            zip_path=args.zip_path,
            github_url=args.github,
            model_name=args.model_name,
        )
    except SemanticJudgeConfigError as error:
        sys.stderr.write(f"[CONFIG_ERROR] {error}\n")
        return 2
    except (SemanticJudgeEvaluationError, ValueError) as error:
        sys.stderr.write(f"[EVALUATION_ERROR] {error}\n")
        return 3
    except (ZipRepositoryError, GitHubRequestError, FileNotFoundError) as error:
        sys.stderr.write(f"[INGESTION_ERROR] {error}\n")
        return 1
    except Exception as error:
        sys.stderr.write(f"[UNEXPECTED_ERROR] {error}\n")
        return 4

    sys.stdout.write(result.model_dump_json(indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

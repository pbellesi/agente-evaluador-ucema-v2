"""CLI de lectura para exponer el evaluador determinístico a un agente externo."""

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.evaluator_engine import run_evaluation, run_zip_evaluation
from src.schema import EvaluationResult


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evalúa un repositorio GitHub o proyecto ZIP con el motor determinístico.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--github", metavar="URL", help="URL pública del repositorio objetivo en GitHub.")
    source.add_argument("--zip", dest="zip_path", metavar="PATH", help="Ruta de un archivo ZIP de proyecto.")
    return parser


def _write_captured_stdout(captured: str) -> None:
    if captured:
        sys.stderr.write(captured)
        if not captured.endswith("\n"):
            sys.stderr.write("\n")


def _invoke_engine(args: argparse.Namespace) -> EvaluationResult:
    captured_stdout = io.StringIO()
    try:
        with redirect_stdout(captured_stdout):
            if args.github:
                result = run_evaluation(args.github)
            else:
                zip_path = Path(args.zip_path)
                result = run_zip_evaluation(zip_path.read_bytes(), zip_path.name)
    finally:
        _write_captured_stdout(captured_stdout.getvalue())

    if not isinstance(result, EvaluationResult):
        raise TypeError("El motor no devolvió un EvaluationResult válido.")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)

    try:
        result = _invoke_engine(args)
    except OSError:
        sys.stderr.write("No se pudo leer el archivo ZIP indicado.\n")
        return 3
    except Exception:
        sys.stderr.write("La herramienta determinística encontró un error inesperado antes de obtener un resultado.\n")
        return 3

    sys.stdout.write(result.model_dump_json() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

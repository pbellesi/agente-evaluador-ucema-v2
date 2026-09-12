"""
Interfaz local Streamlit para el Agente Evaluador UCEMA V2.
Permite evaluar trabajos de forma rápida, determinística y basada en Evidence Dossier.
"""

import hashlib
import os
import sys
import time
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Asegurar carga de .env y resolución de paths
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

from src.batch_evaluator import ProjectEvaluationOutcome
from src.semantic_judge import resolve_gemini_api_key
from src.simple_evaluator import (
    clear_evaluation_cache,
    evaluate_project_zip as evaluate_simple_zip,
    get_runtime_fingerprint,
)

OFFICIAL_PROVIDER = "Gemini"
OFFICIAL_MODEL = "gemini-3.6-flash"


def render_app():
    st.set_page_config(
        page_title="Evaluador UCEMA V2",
        page_icon="🎓",
        layout="wide",
    )

    runtime_fingerprint = get_runtime_fingerprint()

    st.title("Agente Evaluador UCEMA V2")
    st.caption("Evaluación semántica de repositorios mediante LLM y runtime determinístico.")

    api_key = resolve_gemini_api_key()

    # Sidebar: Configuración e Información
    with st.sidebar:
        st.header("Configuración")
        st.info(f"Evaluador: {OFFICIAL_PROVIDER} · {OFFICIAL_MODEL}")
        st.caption(f"Runtime evaluador: `{runtime_fingerprint}`")

        if api_key:
            st.success("GEMINI_API_KEY: Configurada")
        else:
            st.error("GEMINI_API_KEY: No detectada")
            st.warning("Defina GEMINI_API_KEY en variables de entorno, archivo .env o en st.secrets de Streamlit Cloud.")

        st.markdown("---")
        st.markdown(
            "**Pipeline Oficial (1 llamada LLM):**\n"
            "1. Ingesta segura de ZIP en memoria\n"
            "2. Evidence Dossier (inventario y evidencia estructurada)\n"
            f"3. Auditoría y calificación con `{OFFICIAL_MODEL}` ($T=0.0$)\n"
            "4. Validación determinística de contrato y scoring matemático"
        )

        st.markdown("---")
        if st.button("🧹 Limpiar caché de evaluaciones", use_container_width=True):
            clear_evaluation_cache()
            st.session_state["evaluation_cache"] = {}
            st.session_state["outcomes"] = []
            st.success("Caché limpiado correctamente.")
            st.rerun()

    # Verificación de API Key
    if not api_key:
        st.error(
            "⚠️ No se encontró la variable GEMINI_API_KEY. "
            "Por favor, configure GEMINI_API_KEY en las variables de entorno, en el archivo `.env` o en los Secrets de Streamlit Community Cloud para poder ejecutar las evaluaciones."
        )

    # 1. Carga de Archivos
    st.subheader("1. Carga de Proyectos")
    uploaded_files = st.file_uploader(
        "Seleccione uno o más archivos ZIP de proyectos para evaluar",
        type=["zip"],
        accept_multiple_files=True,
        help="Cada archivo ZIP será evaluado de forma completamente independiente.",
    )

    if uploaded_files:
        st.info(f"{len(uploaded_files)} archivo(s) seleccionado(s) para evaluación.")

    # 2. Botón de Ejecución
    st.subheader("2. Ejecución")
    start_eval = st.button(
        "EVALUAR PROYECTOS",
        type="primary",
        disabled=(not uploaded_files) or (not api_key),
    )

    if "outcomes" not in st.session_state:
        st.session_state["outcomes"] = []

    if start_eval and uploaded_files and api_key:
        total_files = len(uploaded_files)
        progress_bar = st.progress(0.0)
        status_box = st.empty()

        outcomes: List[ProjectEvaluationOutcome] = []
        if "evaluation_cache" not in st.session_state:
            st.session_state["evaluation_cache"] = {}

        for idx, uploaded_file in enumerate(uploaded_files):
            zip_bytes = uploaded_file.getvalue()
            zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
            session_cache_key = f"{zip_sha256}:{runtime_fingerprint}:{OFFICIAL_MODEL}"

            if session_cache_key in st.session_state["evaluation_cache"]:
                status_box.info(f"⚡ Recuperando de caché (0 llamadas LLM): **{uploaded_file.name}** ({idx + 1}/{total_files})...")
                outcome = st.session_state["evaluation_cache"][session_cache_key]
            else:
                status_box.info(f"⏳ Evaluando **{uploaded_file.name}** ({idx + 1}/{total_files}): Ingesta -> Evidence Dossier -> Gemini -> Validación...")
                try:
                    res = evaluate_simple_zip(
                        zip_source=zip_bytes,
                        zip_name=uploaded_file.name,
                        api_key=api_key,
                        model_name=OFFICIAL_MODEL,
                    )
                    outcome = ProjectEvaluationOutcome(
                        project_name=uploaded_file.name,
                        status="OK",
                        result=res,
                    )
                    st.session_state["evaluation_cache"][session_cache_key] = outcome
                except Exception as exc:
                    outcome = ProjectEvaluationOutcome(
                        project_name=uploaded_file.name,
                        status="ERROR",
                        error_message=str(exc),
                    )

            outcomes.append(outcome)
            progress_bar.progress((idx + 1) / total_files)

        status_box.success("✅ Evaluación completada para todos los proyectos.")
        st.session_state["outcomes"] = outcomes

    # 3. Tabla Resumen
    if st.session_state.get("outcomes"):
        st.markdown("---")
        st.subheader("3. Resumen de Evaluaciones")

        table_rows = []
        for o in st.session_state["outcomes"]:
            if o.status == "OK" and o.result:
                d1 = o.result.dimensions[0].level_percent if len(o.result.dimensions) > 0 else "-"
                d2 = o.result.dimensions[1].level_percent if len(o.result.dimensions) > 1 else "-"
                d3 = o.result.dimensions[2].level_percent if len(o.result.dimensions) > 2 else "-"
                d4 = o.result.dimensions[3].level_percent if len(o.result.dimensions) > 3 else "-"
                d5 = o.result.dimensions[4].level_percent if len(o.result.dimensions) > 4 else "-"
                final_score = o.result.final_score if o.result.final_score is not None else "-"
                table_rows.append({
                    "Proyecto": o.project_name,
                    "Estado": "OK",
                    "D1": d1,
                    "D2": d2,
                    "D3": d3,
                    "D4": d4,
                    "D5": d5,
                    "Nota final": final_score,
                })
            else:
                table_rows.append({
                    "Proyecto": o.project_name,
                    "Estado": "ERROR",
                    "D1": "-",
                    "D2": "-",
                    "D3": "-",
                    "D4": "-",
                    "D5": "-",
                    "Nota final": "-",
                })

        df_summary = pd.DataFrame(table_rows)
        st.dataframe(
            df_summary,
            use_container_width=True,
            hide_index=True,
        )

        # 4. Detalle por Proyecto
        st.markdown("---")
        st.subheader("4. Detalle por Proyecto")

        for o in st.session_state["outcomes"]:
            header = f"📁 {o.project_name} — Estado: {o.status}"
            if o.status == "OK" and o.result and o.result.final_score is not None:
                header += f" | Nota final: {o.result.final_score}"

            with st.expander(header, expanded=(o.status == "ERROR")):
                if o.status == "ERROR":
                    st.error(f"Error durante la evaluación de este archivo:\n\n{o.error_message}")
                    continue

                res = o.result

                # A. Dimensiones D1-D5
                st.markdown("#### A. DIMENSIONES D1 - D5")
                if res and res.dimensions:
                    for dim in res.dimensions:
                        col_d1, col_d2 = st.columns([1, 4])
                        with col_d1:
                            st.metric(
                                label=f"{dim.dimension} (peso {dim.weight}%)",
                                value=f"{dim.level_percent}%",
                                delta=f"{dim.score} pts",
                            )
                        with col_d2:
                            st.markdown(f"**Justificación:** {dim.justification}")
                            if dim.missing_for_next_level:
                                st.markdown(f"**Faltante para nivel siguiente:** {dim.missing_for_next_level}")
                            else:
                                st.markdown("**Faltante para nivel siguiente:** *Nivel máximo alcanzado (100%)*")
                            if dim.evidence:
                                st.markdown("**Evidencia citada:**")
                                for ev in dim.evidence:
                                    st.markdown(f"  - `{ev}`")
                        st.divider()

                # B. Mejora Prioritaria
                st.markdown("#### B. MEJORA PRIORITARIA")
                if res and res.concrete_improvement:
                    st.info(f"💡 {res.concrete_improvement}")

                # C. Integridad y Telemetría
                st.markdown("#### C. INTEGRIDAD Y TELEMETRÍA")
                st.caption(f"Runtime: `{res.runtime_fingerprint or runtime_fingerprint}` · Modelo: `{res.actual_model_used or OFFICIAL_MODEL}`")
                if res and res.integrity_notes:
                    for note in res.integrity_notes:
                        if "[TELEMETRÍA]" in note or "[INGESTA_ZIP]" in note:
                            st.caption(note)
                        else:
                            st.warning(note)
                else:
                    st.success("Sin anomalías de integridad detectadas.")

                # D. Descargar JSON
                if res:
                    st.download_button(
                        label=f"📥 Descargar JSON ({o.project_name})",
                        data=res.model_dump_json(indent=2),
                        file_name=f"evaluacion_{o.project_name}.json",
                        mime="application/json",
                        key=f"dl_{o.project_name}",
                    )


if __name__ == "__main__":
    render_app()

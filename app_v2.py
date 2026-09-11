"""
Interfaz local Streamlit para el Agente Evaluador UCEMA V2.
Permite ejecutar evaluaciones semánticas locales de archivos ZIP individuales o en lote.
"""

import os
import sys
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

from src.batch_evaluator import (
    ProjectEvaluationOutcome,
    evaluate_project_zip,
    load_rubric_text,
)
from src.semantic_judge import (
    SemanticJudgeConfigError,
    create_semantic_judge,
    resolve_gemini_api_key,
    resolve_gemini_model,
    resolve_llm_provider,
    resolve_nvidia_api_key,
    resolve_nvidia_model,
)


def get_active_provider() -> str:
    return resolve_llm_provider()


def get_provider_details(provider: str) -> tuple[str | None, str, str]:
    if provider == "nvidia":
        return resolve_nvidia_api_key(), resolve_nvidia_model(), "NVIDIA_API_KEY"
    return resolve_gemini_api_key(), resolve_gemini_model(), "GEMINI_API_KEY"


def render_app():
    st.set_page_config(
        page_title="Evaluador UCEMA V2",
        page_icon="🎓",
        layout="wide",
    )

    st.title("Agente Evaluador UCEMA V2")
    st.caption("Evaluación semántica de repositorios mediante LLM y runtime determinístico.")

    provider = get_active_provider()
    api_key, model_name, key_name = get_provider_details(provider)

    # Sidebar: Configuración e Información
    with st.sidebar:
        st.header("Configuración")
        st.text_input(
            "Proveedor LLM",
            value=provider.upper(),
            disabled=True,
            help="Proveedor configurado en LLM_PROVIDER (gemini o nvidia).",
        )
        st.text_input(
            "Modelo configurado",
            value=model_name,
            disabled=True,
            help=f"Modelo utilizado por el Juez Semántico V2 ({key_name.split('_')[0]}_MODEL o default del sistema).",
        )

        if api_key:
            st.success(f"{key_name}: Configurada")
        else:
            st.error(f"{key_name}: No detectada")
            st.warning(f"Defina {key_name} en variables de entorno, archivo .env o en st.secrets de Streamlit Cloud.")

        st.markdown("---")
        st.markdown(
            "**Pipeline V2:**\n"
            "1. Ingesta segura de ZIP en memoria\n"
            "2. ContextBuilder (inventario y contexto)\n"
            f"3. SemanticJudge ({provider.upper()}) (análisis interpretativo)\n"
            "4. EvaluationValidator (verificación y scoring matemático)"
        )

    # Verificación de API Key antes de permitir evaluar
    if not api_key:
        st.error(
            f"⚠️ No se encontró la variable {key_name}. "
            f"Por favor, configure {key_name} en las variables de entorno, en el archivo `.env` o en los Secrets de Streamlit Community Cloud para poder ejecutar las evaluaciones."
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
        try:
            judge = create_semantic_judge(provider=provider, model_name=model_name)
        except SemanticJudgeConfigError as err:
            st.error(f"Error de configuración: {err}")
            return

        rubric_text = load_rubric_text()
        total_files = len(uploaded_files)
        progress_bar = st.progress(0.0)
        status_box = st.empty()

        outcomes: List[ProjectEvaluationOutcome] = []

        for idx, uploaded_file in enumerate(uploaded_files):
            status_box.info(f"⏳ Procesando **{uploaded_file.name}** ({idx + 1}/{total_files})...")
            zip_bytes = uploaded_file.getvalue()

            outcome = evaluate_project_zip(
                zip_bytes=zip_bytes,
                filename=uploaded_file.name,
                judge=judge,
                rubric_text=rubric_text,
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
                payload = o.payload

                # A. Comprensión del proyecto
                st.markdown("#### A. COMPRENSIÓN DEL PROYECTO")
                if payload and payload.project_understanding:
                    pu = payload.project_understanding
                    st.markdown(f"**Resumen del sistema:**\n{pu.system_summary}")
                    st.markdown(f"**Arquitectura observada:**\n{pu.architecture_observed}")
                    if pu.main_technologies:
                        st.markdown(f"**Tecnologías principales:** {', '.join(pu.main_technologies)}")
                else:
                    st.info("Sin datos de comprensión del proyecto.")

                # B. Hallazgos
                st.markdown("#### B. HALLAZGOS")
                if payload and payload.findings:
                    for i, f in enumerate(payload.findings, 1):
                        sev_badge = {
                            "high": "🔴 ALTA",
                            "medium": "🟠 MEDIA",
                            "low": "🟡 BAJA",
                            "info": "🔵 INFO",
                        }.get(f.severity, f.severity.upper())

                        cat_name = f.category.upper()
                        files_str = ", ".join(f.files) if f.files else "Ninguno"

                        with st.container():
                            st.markdown(f"**{i}. [{sev_badge}] Categoría: `{cat_name}`**")
                            st.markdown(f"- **Hallazgo:** {f.finding}")
                            st.markdown(f"- **Archivos de referencia:** `{files_str}`")
                            st.markdown(f"- **Impacto en evaluación:** {f.impact_on_evaluation}")
                            st.markdown("")
                else:
                    st.info("No se registraron hallazgos específicos.")

                # C. Dimensiones D1-D5
                st.markdown("#### C. DIMENSIONES D1 - D5")
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

                # D. Integridad
                st.markdown("#### D. INTEGRIDAD")
                if res and res.integrity_notes:
                    for note in res.integrity_notes:
                        st.warning(note)
                else:
                    st.success("Sin anomalías de integridad detectadas.")

                # E. Mejora Prioritaria
                st.markdown("#### E. MEJORA PRIORITARIA")
                if res and res.concrete_improvement:
                    st.info(f"💡 {res.concrete_improvement}")


if __name__ == "__main__":
    render_app()

import os
import inspect
import subprocess
import sys
import time
from html import escape
from datetime import datetime
import streamlit as st
from src import evidence_extractor
from src.batch_summary import summarize_batch_results
from src.evaluator_engine import evaluate_with_rate_limit_guard, run_evaluation, run_zip_evaluation
from src.schema import EvaluationResult
from src.ui_feedback import clean_text, format_aspect_description, generate_student_feedback

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Agente Evaluador UCEMA",
    page_icon="🎓",
    layout="wide"
)

st.markdown(
    """
    <style>
        :root {
            --ae-ink: #f8fafc;
            --ae-muted: #cbd5e1;
            --ae-muted-strong: #e2e8f0;
            --ae-border: #334155;
            --ae-surface: #17263a;
            --ae-accent: #9f1239;
            --ae-petrol: #102a43;
            --ae-success: #4ade80;
            --ae-warning: #fbbf24;
            --ae-risk: #f87171;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.8rem;
            padding-bottom: 3.4rem;
        }

        .ae-sidebar-control-title {
            color: #f1f5f9;
            font-size: 1rem;
            font-weight: 700;
            margin-top: 0.9rem;
        }

        .ae-sidebar-team-card {
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.18);
            border-radius: 12px;
            color: #f1f5f9;
            margin: 0.9rem 0;
            padding: 0.9rem 1rem;
        }

        .ae-sidebar-team-card h4 {
            color: #f1f5f9;
            font-size: 0.95rem;
            margin: 0 0 0.55rem;
        }

        .ae-sidebar-team-card ul {
            color: #d9e2ea;
            margin: 0;
            padding-left: 1.1rem;
        }

        .ae-hero {
            align-items: center;
            background: var(--ae-petrol);
            border: 1px solid #0b2238;
            border-left: 6px solid var(--ae-accent);
            border-radius: 22px;
            box-shadow: 0 14px 30px rgba(23, 50, 77, 0.18);
            display: flex;
            gap: 1.5rem;
            justify-content: space-between;
            margin-bottom: 2rem;
            padding: 1.8rem 2rem;
        }

        .ae-eyebrow {
            color: #f1c5cd;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .ae-section-label {
            color: var(--ae-accent);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .ae-hero h1 {
            color: #ffffff;
            font-size: 2.55rem;
            letter-spacing: -0.03em;
            line-height: 1.15;
            margin: 0.25rem 0;
        }

        .ae-hero p {
            color: #edf2f6;
            font-size: 1.05rem;
            margin: 0;
        }

        .ae-statuses {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            justify-content: flex-end;
            max-width: 390px;
        }

        .ae-badge {
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.32);
            border-radius: 999px;
            color: #ffffff;
            font-size: 0.82rem;
            font-weight: 650;
            padding: 0.35rem 0.65rem;
            white-space: nowrap;
        }

        [data-testid="stMetric"] {
            border-radius: 14px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.14);
            padding: 0.9rem 1rem;
        }

        [data-testid="stRadio"] [role="radiogroup"] {
            gap: 0.65rem;
        }

        [data-testid="stRadio"] label {
            margin: 0;
            padding: 0.55rem 0.8rem;
        }

        [data-testid="stExpander"] {
            border-radius: 14px;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12);
            margin-bottom: 0.75rem;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 18px;
            box-shadow: 0 7px 18px rgba(0, 0, 0, 0.16);
        }

        [data-testid="stAlert"] {
            border-radius: 10px;
        }

        [data-testid="stDataFrame"] {
            border-radius: 12px;
            overflow: hidden;
        }

        button[kind="primary"] {
            border-radius: 12px;
            box-shadow: 0 6px 14px rgba(80, 10, 30, 0.24);
            font-size: 0.97rem;
            font-weight: 750;
            min-height: 3rem;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            border-radius: 12px;
        }

        .ae-action-kicker {
            color: var(--ae-accent);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
        }

        .ae-action-title {
            color: var(--ae-ink);
            font-size: 1.35rem;
            font-weight: 750;
            margin: 0;
        }

        .ae-action-copy {
            color: var(--ae-muted);
            font-size: 0.95rem;
            margin: 0.35rem 0 1rem;
        }

        .ae-score-card {
            background: var(--ae-surface);
            border: 1px solid var(--ae-border);
            border-left: 5px solid #64748b;
            border-radius: 16px;
            min-height: 132px;
            padding: 1rem 1.05rem;
        }

        .ae-score-card.featured {
            background: #1d3047;
            border-color: #45637e;
            border-left-color: #93c5fd;
            border-top: 4px solid #93c5fd;
            min-height: 138px;
            padding: 1.05rem 1.15rem;
        }

        .ae-score-card.high {
            background: var(--ae-surface);
            border-color: var(--ae-border);
            border-left-color: var(--ae-success);
        }

        .ae-score-card.medium {
            background: var(--ae-surface);
            border-color: var(--ae-border);
            border-left-color: var(--ae-warning);
        }

        .ae-score-card.low {
            background: var(--ae-surface);
            border-color: var(--ae-border);
            border-left-color: var(--ae-risk);
        }

        .ae-score-card .ae-score-label {
            color: var(--ae-muted);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .ae-score-card .ae-score-name {
            color: var(--ae-ink);
            font-size: 0.82rem;
            margin-top: 0.2rem;
            min-height: 2.2rem;
        }

        .ae-score-card .ae-score-value {
            color: var(--ae-ink);
            font-size: 2rem;
            font-weight: 750;
            letter-spacing: -0.04em;
            line-height: 1;
            margin-top: 0.7rem;
        }

        .ae-score-card.featured .ae-score-value {
            font-size: 2.45rem;
        }

        .ae-score-card .ae-score-detail {
            color: var(--ae-muted);
            font-size: 0.78rem;
            margin-top: 0.45rem;
        }

        .ae-feedback-card {
            background: var(--ae-surface);
            border: 1px solid var(--ae-border);
            border-left: 5px solid #64748b;
            border-radius: 14px;
            margin: 0.8rem 0;
            padding: 1rem 1.1rem 0.85rem;
        }

        .ae-feedback-card h3 {
            color: var(--ae-ink);
            font-size: 1.04rem;
            margin: 0 0 0.55rem;
        }

        .ae-feedback-card p,
        .ae-feedback-card ul {
            color: var(--ae-ink);
            margin-bottom: 0.25rem;
        }

        .ae-feedback-card.strength {
            background: var(--ae-surface);
            border-color: var(--ae-border);
            border-left-color: var(--ae-success);
        }

        .ae-feedback-card.improvement {
            background: var(--ae-surface);
            border-color: var(--ae-border);
            border-left-color: var(--ae-warning);
        }

        .ae-feedback-card.priority {
            background: #251927;
            border-color: #713448;
            border-left: 5px solid var(--ae-accent);
        }

        .ae-feedback-card.summary {
            background: var(--ae-surface);
            border-color: var(--ae-border);
            border-left-color: var(--ae-petrol);
        }

        .ae-feedback-card.integrity {
            background: #241d26;
            border-color: #744454;
            border-left-color: var(--ae-risk);
        }

        .ae-footer {
            border-top: 1px solid var(--ae-border);
            color: var(--ae-muted-strong);
            font-size: 0.82rem;
            margin-top: 2.5rem;
            padding-top: 1rem;
            text-align: center;
        }

        @media (max-width: 760px) {
            .ae-hero {
                align-items: flex-start;
                flex-direction: column;
            }

            .ae-statuses {
                justify-content: flex-start;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def _visual_tone(level_percent):
    """Selecciona solamente el tratamiento visual de una tarjeta."""
    level = level_percent or 0
    if level >= 75:
        return "high"
    if level >= 50:
        return "medium"
    return "low"


def _render_score_card(label, name, value, detail, level_percent, featured=False):
    """Renderiza valores ya calculados sin alterar la evaluación."""
    featured_class = " featured" if featured else ""
    st.markdown(
        f"""
        <section class="ae-score-card {_visual_tone(level_percent)}{featured_class}">
            <div class="ae-score-label">{escape(str(label))}</div>
            <div class="ae-score-name">{escape(str(name))}</div>
            <div class="ae-score-value">{escape(str(value))}</div>
            <div class="ae-score-detail">{escape(str(detail))}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_feedback_card(title, tone, body_html):
    """Agrupa la devolución existente en un bloque visual docente."""
    st.markdown(
        f"""
        <section class="ae-feedback-card {tone}">
            <h3>{escape(title)}</h3>
            {body_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


def _feedback_list(items):
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _display_text(text):
    """Normaliza sólo la tipografía de textos ya producidos por el feedback."""
    return escape(clean_text(str(text or "")).replace("**", "")).replace("\n", "<br>")


def _format_dashboard_score(value):
    return f"{value:.2f}" if value is not None else "No disponible"


def _render_batch_dashboard(batch_results):
    """Presenta estadísticas de resultados existentes sin reevaluar el lote."""
    summary = summarize_batch_results(batch_results, approval_threshold=0)

    st.subheader("Resumen del lote")
    st.caption("Vista general de los trabajos evaluados")

    primary_metrics = st.columns(4)
    primary_metrics[0].metric("Procesados", summary["processed_count"])
    primary_metrics[1].metric("Evaluados", summary["valid_count"])
    primary_metrics[2].metric("Errores", summary["access_error_count"])
    primary_metrics[3].metric("Nota promedio", _format_dashboard_score(summary["mean_score"]))

    approval_threshold = st.slider(
        "Umbral de aprobación",
        min_value=0,
        max_value=100,
        value=60,
        key="batch_approval_threshold",
    )
    st.caption(
        "Umbral configurable para este resumen. No modifica la evaluación ni representa "
        "necesariamente el criterio oficial de aprobación."
    )
    summary = summarize_batch_results(batch_results, approval_threshold=approval_threshold)

    academic_metrics = st.columns(3)
    academic_metrics[0].metric("Mediana", _format_dashboard_score(summary["median_score"]))
    academic_metrics[1].metric("Aprobados", summary["approved_count"] if summary["valid_count"] else "No disponible")
    approval_rate = (
        f"{summary['approval_rate'] * 100:.1f}%"
        if summary["approval_rate"] is not None
        else "No disponible"
    )
    academic_metrics[2].metric("Tasa de aprobación", approval_rate)

    if not summary["valid_count"]:
        st.info("No hay evaluaciones válidas para calcular estadísticas académicas o promedios por dimensión.")
        return

    chart_rows = []
    for index, average in enumerate(summary["dimension_averages"]):
        if average is None:
            continue
        canonical_name = summary["dimension_names"][index]
        label = f"D{index + 1} · {canonical_name}" if canonical_name else f"D{index + 1}"
        rounded_average = round(average, 2)
        chart_rows.append(
            {
                "dimensión": label,
                "promedio": rounded_average,
                "etiqueta": f"{rounded_average:.1f}",
                "posición_etiqueta": min(rounded_average + 3, 98),
                "orden": index + 1,
            }
        )

    if chart_rows:
        st.subheader("Promedio por dimensión")
        st.vega_lite_chart(
            chart_rows,
            {
                "layer": [
                    {
                        "mark": {"type": "bar", "color": "#9F1239", "cornerRadiusEnd": 3},
                        "encoding": {
                            "x": {
                                "field": "dimensión",
                                "type": "nominal",
                                "sort": {"field": "orden", "order": "ascending"},
                                "title": None,
                            },
                            "y": {
                                "field": "promedio",
                                "type": "quantitative",
                                "scale": {"domain": [0, 100]},
                                "title": "Promedio (%)",
                            },
                            "tooltip": [
                                {"field": "dimensión", "type": "nominal", "title": "Dimensión"},
                                {"field": "promedio", "type": "quantitative", "title": "Promedio (%)"},
                            ],
                        },
                    },
                    {
                        "mark": {
                            "type": "text",
                            "color": "#F8FAFC",
                            "fontWeight": 700,
                            "baseline": "bottom",
                        },
                        "encoding": {
                            "x": {
                                "field": "dimensión",
                                "type": "nominal",
                                "sort": {"field": "orden", "order": "ascending"},
                            },
                            "y": {
                                "field": "posición_etiqueta",
                                "type": "quantitative",
                                "scale": {"domain": [0, 100]},
                            },
                            "text": {"field": "etiqueta", "type": "nominal"},
                        },
                    },
                ],
                "height": 260,
            },
            use_container_width=True,
        )


def _render_batch_results(batch_results, run_metadata):
    """Renderiza un lote ya procesado; no consulta ni vuelve a evaluar repositorios."""
    batch_status = summarize_batch_results(batch_results, approval_threshold=60)
    if batch_status["valid_count"]:
        _render_batch_dashboard(batch_results)
    else:
        st.subheader("Estado del lote")
        status_metrics = st.columns(2)
        status_metrics[0].metric("Procesados", batch_status["processed_count"])
        status_metrics[1].metric("Errores", batch_status["access_error_count"])
        st.info("No hay evaluaciones válidas para calcular estadísticas académicas del lote.")
    st.caption(
        f"URLs recibidas: {run_metadata['urls_received']} · "
        f"URLs únicas procesadas: {run_metadata['processed_urls']} · "
        f"Tiempo total: {run_metadata['total_elapsed_time']:.2f} s · "
        f"Tiempo promedio: {run_metadata['average_time']:.2f} s · "
        "Tokens generativos: 0 · Costo API generativo: USD 0.00"
    )
    st.divider()

    st.subheader("📑 Detalle de trabajos")
    table_rows = []
    for index, result in enumerate(batch_results, start=1):
        dimensions = result.dimensions
        dimension_scores = [
            f"{dimensions[position].score:.2f}"
            if len(dimensions) > position and dimensions[position].score is not None
            else "0.00"
            for position in range(5)
        ]
        status_detail = result.evaluation_status.upper()
        if result.evaluation_status != "completed" and result.integrity_notes:
            status_detail = f"{status_detail}: {result.integrity_notes[0]}"
        table_rows.append(
            {
                "#": index,
                "repositorio": result.repository,
                "revisión evaluada": result.evaluated_revision,
                "estado / error": status_detail,
                "nota final": f"{result.final_score:.2f}" if result.final_score is not None else "N/A",
                "D1": dimension_scores[0],
                "D2": dimension_scores[1],
                "D3": dimension_scores[2],
                "D4": dimension_scores[3],
                "D5": dimension_scores[4],
            }
        )
    st.dataframe(table_rows, use_container_width=True)

    st.subheader("🎓 Devolución por trabajo")
    st.caption("Abrí cada trabajo para consultar la devolución docente, fortalezas y próximas acciones.")
    for result in batch_results:
        score_label = f"{result.final_score:.2f} puntos" if result.final_score is not None else "sin puntaje"
        with st.expander(f"▶ {result.repository} — {score_label}", expanded=False):
            if result.evaluation_status != "completed":
                error_detail = "; ".join(result.integrity_notes) or "No se pudo completar la evaluación."
                st.error(error_detail)
                continue
            if not result.dimensions:
                st.warning("La evaluación finalizó sin dimensiones para generar devolución.")
                continue

            feedback = generate_student_feedback(result)
            _render_feedback_card(
                "Devolución al alumno",
                "summary",
                f"<p>{_display_text(feedback['resumen_general'])}</p>",
            )
            strengths = sorted(
                [dimension for dimension in result.dimensions if dimension.level_percent == 100],
                key=lambda dimension: (dimension.level_percent, dimension.weight),
                reverse=True,
            )[:3]
            if strengths:
                strength_items = []
                for strength in strengths:
                    evidence = strength.evidence[0] if strength.evidence else "Sin evidencia citada"
                    strength_items.append(
                        f"<strong>{escape(strength.dimension)}</strong> "
                        f"({strength.level_percent}%): {_display_text(strength.justification)} "
                        f"<span>— Evidencia: {escape(evidence)}</span>"
                    )
                _render_feedback_card("✅ Fortalezas", "strength", _feedback_list(strength_items))
            else:
                st.caption("No se identificaron fortalezas suficientemente demostradas.")

            improvement_dimensions = sorted(
                [
                    (index, dimension)
                    for index, dimension in enumerate(result.dimensions)
                    if (dimension.level_percent or 0) < 100
                ],
                key=lambda item: ((item[1].level_percent or 0), item[0]),
            )[:3]
            if improvement_dimensions:
                improvement_items = [
                    (
                        f"<strong>{escape(aspect.dimension)}</strong> "
                        f"({aspect.level_percent}%): "
                        f"{_display_text(format_aspect_description(aspect))}"
                    )
                    for _, aspect in improvement_dimensions
                ]
                _render_feedback_card(
                    "⚠ Aspectos a mejorar",
                    "improvement",
                    _feedback_list(improvement_items),
                )
            else:
                st.caption("No se identificaron aspectos pendientes.")

            _, weakest_dimension = min(
                enumerate(result.dimensions),
                key=lambda item: ((item[1].level_percent or 0), item[0]),
            )
            priority = clean_text(format_aspect_description(weakest_dimension)) or feedback["recomendacion_prioritaria"]
            _render_feedback_card(
                "🎯 Prioridad principal",
                "priority",
                f"<p><strong>{escape(weakest_dimension.dimension)}:</strong> {_display_text(priority)}</p>",
            )


def _render_evaluation_result(result, technical_mode, evaluation_diagnostics):
    """Presenta un EvaluationResult sin distinguir su fuente de entrada."""
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"📌 Repositorio: `{result.repository}`")
        st.caption(f"Revisión evaluada: `{result.evaluated_revision}` | Fecha: `{result.evaluation_date}`")
        retrieval = (evaluation_diagnostics or {}).get("retrieval", {})
        if retrieval.get("source") == "ZIP":
            st.caption(
                f"Origen: ZIP | Archivo: `{retrieval.get('source_filename', result.repository)}` | "
                f"Huella SHA-256: `{result.evaluated_revision}`"
            )
    with col2:
        status_color = "green" if result.evaluation_status == "completed" else "red"
        st.markdown(f"**Estado:** :{status_color}[{result.evaluation_status.upper()}]")
    with col3:
        if result.final_score is not None:
            _render_score_card("Nota final", "Resultado global", f"{result.final_score:.2f}", "sobre 100 puntos", result.final_score, featured=True)
        else:
            _render_score_card("Nota final", "Resultado global", "N/A", "sin puntaje disponible", 0, featured=True)

    if technical_mode:
        with st.expander("🔍 Diagnóstico de la corrida", expanded=False):
            st.json(evaluation_diagnostics or {"status": "No disponible: la evaluación no produjo datos de diagnóstico."})

    st.subheader("📊 Resultado por dimensiones")
    st.caption("Lectura compacta de las cinco dimensiones oficiales de la rúbrica.")
    if result.dimensions:
        d_cols = st.columns(len(result.dimensions))
        for idx, dim in enumerate(result.dimensions):
            with d_cols[idx]:
                _render_score_card(f"D{idx + 1}", dim.dimension, f"{dim.level_percent or 0}%", f"{dim.score:.2f} puntos" if dim.score is not None else "0.00 puntos", dim.level_percent)

    feedback = generate_student_feedback(result)
    st.divider()
    st.subheader("🎓 Devolución para el trabajo evaluado")
    _render_feedback_card("Devolución al alumno", "summary", f"<p>{_display_text(feedback['resumen_general'])}</p>")

    if feedback["fortalezas"]:
        strength_items = [f"<strong>{escape(f['dimension'])}</strong> ({f['level_percent']}%): {_display_text(f['text'])}" for f in feedback["fortalezas"]]
        _render_feedback_card("✅ Fortalezas", "strength", _feedback_list(strength_items))
    if feedback["avances_parciales"]:
        partial_items = [f"<strong>{escape(a['dimension'])}</strong> ({a['level_percent']}%): {_display_text(a['text'])}" for a in feedback["avances_parciales"]]
        _render_feedback_card("📈 Avances parciales", "summary", _feedback_list(partial_items))
    if feedback["aspectos_a_mejorar"]:
        improvement_items = [f"<strong>{escape(m['dimension'])}</strong> (nivel actual: {m['level_percent']}%): {_display_text(m['text'])}" for m in feedback["aspectos_a_mejorar"]]
        _render_feedback_card("⚠ Aspectos a mejorar", "improvement", _feedback_list(improvement_items))
    if feedback["recomendacion_prioritaria"]:
        _render_feedback_card("🎯 Prioridad principal", "priority", f"<p>{_display_text(feedback['recomendacion_prioritaria'])}</p>")
    if feedback["tiene_contradicciones"]:
        integrity_items = [_display_text(note) for note in feedback["contradicciones"]]
        _render_feedback_card(
            "🔎 Evidencia que requiere revisión",
            "integrity",
            "<p>Se identificaron inconsistencias objetivas entre los artefactos documentados y la implementación ejecutable.</p>" + _feedback_list(integrity_items),
        )

    st.divider()
    with st.expander("📚 Evidencia y justificación por dimensión", expanded=False):
        if not result.dimensions:
            st.error("No se obtuvieron dimensiones evaluadas debido a un error de acceso.")
        else:
            for dim in result.dimensions:
                st.markdown(f"### **{dim.dimension}** — Puntaje: `{dim.score if dim.score is not None else 0}` / {dim.weight} pts (Nivel {dim.level_percent if dim.level_percent is not None else 0}%)")
                d_col1, d_col2 = st.columns([1, 2])
                with d_col1:
                    st.markdown(f"**Peso:** {dim.weight} pts")
                    st.markdown(f"**Nivel asignado:** {dim.level_percent}%")
                    st.markdown(f"**Puntaje parcial:** {dim.score} pts")
                with d_col2:
                    st.markdown("**Justificación:**")
                    st.write(dim.justification)
                    if dim.missing_for_next_level:
                        st.markdown("**Faltante para el siguiente nivel:**")
                        st.caption(dim.missing_for_next_level)
                st.markdown("**Evidencia citada:**")
                if dim.evidence:
                    for ev in dim.evidence:
                        st.markdown(f"- `{ev}`")
                else:
                    st.write("_Sin evidencia citada_")
                st.divider()


st.markdown(
    """
    <section class="ae-hero">
        <div>
            <div class="ae-eyebrow">UCEMA · Programación de y con Agentes de IA</div>
            <h1>Agente Evaluador</h1>
            <p>Evaluación objetiva, trazable y reproducible de trabajos finales.</p>
        </div>
        <div class="ae-statuses" aria-label="Estado del sistema">
            <span class="ae-badge">Motor determinístico</span>
            <span class="ae-badge">0 tokens generativos</span>
            <span class="ae-badge">USD 0 API generativa</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

# Sidebar informativa
with st.sidebar:
    logo_path = os.path.join("assets", "ucema_logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=160)

    st.markdown("### Configuración")
    st.caption("Elegí el modo de evaluación desde las pestañas principales.")

    st.markdown("### Modos de evaluación")
    st.caption("Individual: un repositorio. Lote: hasta 50 repositorios en una misma corrida.")

    st.markdown('<div class="ae-sidebar-control-title">Modo técnico</div>', unsafe_allow_html=True)
    st.caption("Opcional. No modifica la evaluación.")

    technical_mode = st.toggle(
        "Modo técnico",
        value=False,
        help="Muestra diagnósticos de runtime y de corrida. No altera la evaluación.",
        key="technical_mode",
        label_visibility="collapsed",
    )

    if technical_mode:
        with st.expander("🛠️ Diagnóstico técnico", expanded=False):
            try:
                runtime_head = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                    capture_output=True,
                    check=True,
                    text=True,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError) as error:
                runtime_head = f"No disponible: {error}"

            contextual_patterns = [
                r"r'\bplaceholder\b.{0,80}\b(?:conector|connector|api|integraci[oó]n)\b'",
                r"r'\b(?:conector|connector|api|integraci[oó]n)\b.{0,80}\bplaceholder\b'",
            ]
            try:
                extractor_source = inspect.getsource(evidence_extractor)
                generic_placeholder_pattern = "r'placeholder'" in extractor_source
                contextual_placeholder_patterns = [
                    pattern in extractor_source for pattern in contextual_patterns
                ]
                source_error = None
            except (OSError, TypeError) as error:
                generic_placeholder_pattern = None
                contextual_placeholder_patterns = None
                source_error = str(error)
            st.json(
                {
                    "runtime_git_head": runtime_head,
                    "evidence_extractor_module": evidence_extractor.__file__,
                    "generic_placeholder_pattern": generic_placeholder_pattern,
                    "contextual_placeholder_patterns": contextual_placeholder_patterns,
                    "source_inspection_error": source_error,
                    "python_version": sys.version,
                }
            )

    st.divider()

    st.markdown(
        """
        <section class="ae-sidebar-team-card">
            <h4>👥 Equipo · Agente Evaluador</h4>
            <ul>
                <li>Pablo Bellesi</li>
                <li>Diego Mendez</li>
                <li>Franco Gambini</li>
                <li>Sofia Mapelli</li>
                <li>Franco Forziati</li>
                <li>Melisa Clark</li>
            </ul>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Principios")
    st.markdown("""
    - **Evidencia > declaración**
    - Scoring determinístico en Python
    - Cinco dimensiones de la rúbrica
    - Sin API generativa en runtime
    """)

evaluation_mode = st.radio(
    "Modo de evaluación",
    ["📌 Evaluación Individual", "📋 Evaluación por Lote", "📦 Proyecto ZIP"],
    horizontal=True,
    label_visibility="collapsed",
    key="evaluation_mode",
)

if evaluation_mode == "📌 Evaluación Individual":
    st.markdown('<div class="ae-section-label">Evaluación individual</div>', unsafe_allow_html=True)
    st.caption("Ingresá una URL pública de GitHub para obtener una evaluación trazable a su revisión exacta.")

    with st.container(border=True):
        st.markdown('<div class="ae-action-kicker">Punto de partida</div>', unsafe_allow_html=True)
        st.markdown('<p class="ae-action-title">Evaluá un repositorio</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="ae-action-copy">Pegá la URL pública de GitHub. El resultado queda trazado a la revisión evaluada.</p>',
            unsafe_allow_html=True,
        )
        repo_url = st.text_input(
            "URL pública del repositorio objetivo en GitHub",
            placeholder="https://github.com/propietario/trabajo-final",
            help="Ingresa la URL del repositorio individual o subcarpeta (/tree/branch/subpath) a evaluar",
            key="input_single_url"
        )
        evaluate_requested = st.button(
            "🚀 Evaluar repositorio",
            type="primary",
            use_container_width=True,
            key="btn_single_eval",
        )

    if evaluate_requested:
        if not repo_url.strip():
            st.error("Por favor, ingresa una URL válida de GitHub.")
        else:
            evaluation_diagnostics = {}
            with st.status("Evaluando repositorio...", expanded=True) as status:
                st.write("🔍 Inspeccionando árbol y archivos del repositorio...")
                st.write("📜 Extrayendo evidencia objetiva y aplicando gates determinísticos...")
                
                result = run_evaluation(
                    repo_url=repo_url.strip(),
                    status_callback=lambda msg: st.write(f"⏳ {msg}"),
                    diagnostics_callback=lambda data: evaluation_diagnostics.update(data),
                )
                
                if result.evaluation_status == "completed":
                    status.update(label="✅ Evaluación completada con éxito", state="complete", expanded=False)
                else:
                    status.update(label="❌ Error durante la evaluación", state="error", expanded=True)

            _render_evaluation_result(result, technical_mode, evaluation_diagnostics)

elif evaluation_mode == "📦 Proyecto ZIP":
    st.markdown('<div class="ae-section-label">Evaluación de archivo ZIP</div>', unsafe_allow_html=True)
    st.caption("Cargá un proyecto ZIP. Se inspecciona como evidencia sin ejecutar su contenido.")
    with st.container(border=True):
        uploaded_zip = st.file_uploader(
            "Archivo ZIP del proyecto",
            type=["zip"],
            accept_multiple_files=False,
            key="input_zip_project",
        )
        if uploaded_zip is not None:
            st.caption(f"Archivo: `{uploaded_zip.name}` | Tamaño: {uploaded_zip.size:,} bytes")
        evaluate_zip_requested = st.button(
            "📦 Evaluar proyecto ZIP",
            type="primary",
            use_container_width=True,
            key="btn_zip_eval",
        )

    if evaluate_zip_requested:
        if uploaded_zip is None:
            st.error("Seleccioná un archivo .zip antes de evaluar.")
        else:
            evaluation_diagnostics = {
                "retrieval": {"source": "ZIP", "source_filename": uploaded_zip.name},
            }
            with st.status("Evaluando archivo ZIP...", expanded=True) as status:
                st.write("🛡️ Validando estructura y seguridad del ZIP sin ejecutar contenido...")
                st.write("📜 Extrayendo evidencia objetiva y aplicando gates determinísticos...")
                result = run_zip_evaluation(
                    uploaded_zip.getvalue(),
                    uploaded_zip.name,
                    status_callback=lambda msg: st.write(f"⏳ {msg}"),
                    diagnostics_callback=lambda data: evaluation_diagnostics.update(data),
                )
                if result.evaluation_status == "completed":
                    status.update(label="✅ Evaluación completada con éxito", state="complete", expanded=False)
                else:
                    status.update(label="❌ Error durante la evaluación", state="error", expanded=True)
            _render_evaluation_result(result, technical_mode, evaluation_diagnostics)

else:
    st.markdown('<div class="ae-section-label">Evaluación por lote</div>', unsafe_allow_html=True)
    st.subheader("📋 Evaluación de repositorios")
    st.caption("Ingresá hasta 50 URLs públicas de GitHub, una por línea. Todas se evalúan con el mismo motor determinístico.")

    batch_input = st.text_area(
        "URLs públicas de GitHub (una por línea, máx. 50)",
        placeholder="https://github.com/propietario/repo-1\nhttps://github.com/propietario/repo-2\nhttps://github.com/propietario/repo-3",
        height=200,
        key="input_batch_urls"
    )

    if st.button("🚀 Evaluar Lote", type="primary", use_container_width=True, key="btn_batch_eval"):
        raw_urls = [line.strip() for line in batch_input.splitlines() if line.strip()]
        urls_received = len(raw_urls)

        if urls_received == 0:
            st.error("Por favor, ingresa al menos una URL válida de GitHub.")
        else:
            # Deduplicar preservando el orden de aparición
            unique_urls = list(dict.fromkeys(raw_urls))
            dedup_count = urls_received - len(unique_urls)

            # Cap a máximo 50 URLs
            valid_urls = unique_urls[:50]
            capped_count = len(unique_urls) - len(valid_urls)

            if dedup_count > 0:
                st.info(f"ℹ️ Se eliminaron {dedup_count} URL(s) duplicada(s) del lote.")
            if capped_count > 0:
                st.warning(f"⚠️ Se excedió el límite de 50 URLs. Se evaluarán únicamente las primeras 50 URLs únicas.")

            st.write(f"▶️ Procesando **{len(valid_urls)}** repositorio(s)...")

            progress_bar = st.progress(0.0)
            status_text = st.empty()

            batch_results = []
            completed_count = 0
            error_count = 0
            primary_rate_limit_active = False

            start_time = time.time()
            total_urls = len(valid_urls)

            for idx, url in enumerate(valid_urls, start=1):
                status_text.write(f"⏳ ({idx}/{total_urls}) Evaluando `{url}`...")
                try:
                    res, primary_rate_limit_active = evaluate_with_rate_limit_guard(
                        url,
                        primary_rate_limit_active,
                    )
                except Exception as e:
                    res = EvaluationResult(
                        repository=url,
                        evaluated_revision="unknown",
                        evaluation_date=datetime.now().strftime("%Y-%m-%d"),
                        evaluation_status="access_error",
                        dimensions=[],
                        final_score=None,
                        concrete_improvement="Error no controlado durante la evaluación del repositorio.",
                        integrity_notes=[f"Excepción en ejecución batch: {str(e)}"]
                    )

                if res.evaluation_status == "completed":
                    completed_count += 1
                else:
                    error_count += 1

                batch_results.append(res)
                progress_bar.progress(idx / total_urls)

            total_elapsed_time = time.time() - start_time
            avg_time = total_elapsed_time / total_urls if total_urls > 0 else 0.0

            status_text.success("✅ Evaluación del lote completada con éxito.")
            st.session_state["batch_results"] = batch_results
            st.session_state["batch_run_metadata"] = {
                "urls_received": urls_received,
                "processed_urls": total_urls,
                "total_elapsed_time": total_elapsed_time,
                "average_time": avg_time,
            }

    saved_batch_results = st.session_state.get("batch_results")
    saved_batch_metadata = st.session_state.get("batch_run_metadata")
    if saved_batch_results is not None and saved_batch_metadata is not None:
        st.divider()
        _render_batch_results(saved_batch_results, saved_batch_metadata)

st.markdown(
    """
    <footer class="ae-footer">
        Equipo Agente Evaluador · Programación de y con Agentes de IA · UCEMA ·
        Evaluador V2 · Runtime determinístico · 0 tokens generativos
    </footer>
    """,
    unsafe_allow_html=True,
)


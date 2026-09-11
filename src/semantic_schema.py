from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

FindingCategory = Literal[
    "implementation",
    "process",
    "reproducibility",
    "economics",
    "governance",
    "integrity",
    "other",
]

FindingSeverity = Literal["info", "low", "medium", "high"]

ValidLevel = Literal[0, 25, 50, 75, 100]


class ProjectUnderstanding(BaseModel):
    system_summary: str = Field(..., description="Resumen conciso del sistema implementado")
    architecture_observed: str = Field(..., description="Descripción de la arquitectura observada en el repositorio")
    main_technologies: List[str] = Field(default_factory=list, description="Principales librerías, stacks o tecnologías")


class FindingItem(BaseModel):
    category: FindingCategory = Field(..., description="Categoría temática del hallazgo")
    severity: FindingSeverity = Field(..., description="Severidad del hallazgo (info, low, medium, high)")
    files: List[str] = Field(default_factory=list, description="Rutas de los archivos relevantes para este hallazgo")
    finding: str = Field(..., description="Descripción concreta de la evidencia observada, ausencia o discrepancia")
    impact_on_evaluation: str = Field(..., description="Efecto cualitativo del hallazgo en la evaluación")


class DimensionEvaluation(BaseModel):
    recommended_level: ValidLevel = Field(..., description="Nivel asignado estrictamente en 0, 25, 50, 75 o 100")
    justification: str = Field(..., description="Justificación detallada sustentada en los hallazgos observacionales")
    missing_for_next_level: Optional[str] = Field(
        None, description="Artefacto o evidencia observable requerida para el siguiente nivel, o null si es 100"
    )


class SemanticJudgePayload(BaseModel):
    project_understanding: ProjectUnderstanding = Field(..., description="Comprensión global previa del proyecto")
    findings: List[FindingItem] = Field(default_factory=list, description="Lista flexible de hallazgos observacionales")
    dimension_evaluations: Dict[str, DimensionEvaluation] = Field(
        ..., description="Evaluación fundamentada de las dimensiones oficiales D1 a D5"
    )
    concrete_improvement: str = Field(..., description="Exactamente una recomendación prioritaria, concreta y verificable")

    @field_validator("dimension_evaluations")
    @classmethod
    def validate_dimension_keys(cls, v: Dict[str, DimensionEvaluation]) -> Dict[str, DimensionEvaluation]:
        expected_keys = {"D1", "D2", "D3", "D4", "D5"}
        if set(v.keys()) != expected_keys:
            raise ValueError(f"dimension_evaluations must contain exactly {expected_keys}, got {set(v.keys())}")
        return v

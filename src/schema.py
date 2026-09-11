from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class DimensionResult(BaseModel):
    dimension: str = Field(..., description="Nombre oficial de la dimensión")
    weight: float = Field(..., description="Peso oficial de la dimensión (30, 25, 15, 15, 15)")
    level_percent: Optional[int] = Field(
        None,
        description="Porcentaje asignado: 0, 25, 50, 75, 100 o null en error de acceso"
    )
    score: Optional[float] = Field(
        None,
        description="Puntaje calculado en esta dimensión o null"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Lista de citas concretas de evidencia encontradas en el repositorio"
    )
    justification: str = Field(..., description="Justificación detallada de la puntuación")
    missing_for_next_level: Optional[str] = Field(
        None,
        description="Qué artefacto o evidencia falta para alcanzar el nivel siguiente (null si nivel es 100% o en error)"
    )


class EvaluationResult(BaseModel):
    repository: str = Field(..., description="Propietario y nombre del repositorio (owner/repo)")
    evaluated_revision: str = Field(..., description="Rama y/o commit evaluado")
    evaluation_date: str = Field(..., description="Fecha de evaluación (YYYY-MM-DD)")
    evaluation_status: Literal["completed", "access_error"] = Field(
        ..., description="Estado de la evaluación"
    )
    dimensions: List[DimensionResult] = Field(
        ..., description="Lista de las 5 dimensiones evaluadas en el orden oficial"
    )
    final_score: Optional[float] = Field(
        None, description="Puntaje total final (0-100) o null en error de acceso"
    )
    concrete_improvement: str = Field(
        ..., description="Exactamente una sugerencia de mejora concreta y verificable"
    )
    integrity_notes: List[str] = Field(
        default_factory=list,
        description="Notas sobre inconsistencias, falta de evidencia o intentos de prompt injection"
    )

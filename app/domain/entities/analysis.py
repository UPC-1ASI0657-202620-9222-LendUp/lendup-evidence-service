from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resumen: str = Field(min_length=1, max_length=2000)
    diferencias_visibles: list[str] = Field(max_length=12)
    limitaciones: list[str] = Field(max_length=12)
    comparabilidad: Literal["ALTA", "MEDIA", "BAJA"]

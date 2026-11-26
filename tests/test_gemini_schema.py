from google.genai import types
import pytest
from pydantic import ValidationError

from app.domain.entities.analysis import AnalysisResult
from app.infrastructure.gemini.adapter import response_schema


def test_provider_schema_uses_supported_subset():
    schema = response_schema().model_dump(mode="json", exclude_none=True)
    assert schema["type"] == "OBJECT"
    assert "additional_properties" not in schema
    assert set(schema["required"]) == set(AnalysisResult.model_fields)
    assert schema["properties"]["comparabilidad"]["enum"] == ["ALTA", "MEDIA", "BAJA"]
    assert schema["properties"]["limitaciones"]["items"]["type"] == "STRING"
    config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=response_schema())
    assert config.response_schema is not None


def test_local_schema_still_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AnalysisResult.model_validate_json(
            '{"resumen":"Visible","diferencias_visibles":[],"limitaciones":[],"comparabilidad":"MEDIA","culpable":"usuario"}'
        )

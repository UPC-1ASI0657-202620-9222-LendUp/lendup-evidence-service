from enum import Enum


class IncidentType(str, Enum):
    DAMAGE = "DANIO"
    LOSS = "PERDIDA"
    DELAY = "RETRASO"
    NOT_RETURNED = "NO_DEVOLUCION"
    OTHER = "OTRO"


def clean_content(value: str, minimum: int) -> str:
    value = value.strip()
    if not minimum <= len(value) <= 10000:
        raise ValueError(f"El contenido debe tener entre {minimum} y 10000 caracteres")
    return value


class IncidentState(str, Enum):
    PENDING = "PENDIENTE"
    IN_REVIEW = "EN_REVISION"
    RESOLVED = "RESUELTA"


class GuaranteeDecision(str, Enum):
    NONE = "SIN_AFECTACION"
    PARTIAL = "AFECTACION_PARCIAL"
    TOTAL = "AFECTACION_TOTAL"

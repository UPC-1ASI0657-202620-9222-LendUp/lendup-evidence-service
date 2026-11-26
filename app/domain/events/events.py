"""Versioned integration events for Evidence and Incident."""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.entities.resolution import money

ROUTES = {
    "EvidenciaRegistrada": "evidencias.evidencia-registrada.v1",
    "IncidenciaReportada": "evidencias.incidencia-reportada.v1",
    "IncidenciaResuelta": "evidencias.incidencia-resuelta.v1",
}


def identifier(value):
    return str(UUID(str(value)))


def envelope(kind, aggregate_id, version, payload, correlation_id=None):
    if kind not in ROUTES:
        raise ValueError("Unsupported event")
    return dict(event_id=str(uuid4()), event_type=kind, event_version=1,
                aggregate_version=version, aggregate_id=identifier(aggregate_id),
                occurred_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                correlation_id=identifier(correlation_id) if correlation_id else str(uuid4()),
                payload=payload)


def evidence_registered(record):
    payload = dict(evidencia_id=identifier(record["id"]), prestamo_id=identifier(record["prestamo_id"]),
                   registrada_por_usuario_id=identifier(record["registrada_por_usuario_id"]),
                   etapa=record["etapa"], tipo=record["tipo"])
    if record.get("incidencia_id"):
        payload["incidencia_id"] = identifier(record["incidencia_id"])
    return envelope("EvidenciaRegistrada", record["id"], 1, payload)


def incident_event(incident, loan, resolved=False):
    payload = dict(incidencia_id=identifier(incident["id"]), prestamo_id=identifier(incident["prestamo_id"]),
                   prestamista_usuario_id=identifier(loan["prestamista_usuario_id"]),
                   prestatario_usuario_id=identifier(loan["prestatario_usuario_id"]))
    if resolved:
        payload.update(decision_garantia=incident["decision_garantia"],
                       monto_garantia_afectado=float(money(incident["monto_garantia_afectado"])),
                       moneda=incident["moneda"],
                       justificacion_resolucion=incident["justificacion_resolucion"])
    else:
        payload.update(tipo=incident["tipo"], reportada_por_usuario_id=identifier(incident["reportada_por_usuario_id"]))
    return envelope("IncidenciaResuelta" if resolved else "IncidenciaReportada",
                    incident["id"], 2 if resolved else 1, payload, incident["id"])

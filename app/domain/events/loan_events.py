"""Fields consumed from the Loans v1 published event contract."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

ROUTES = dict(zip(
    ("creado", "objeto-entregado", "activado", "extension-solicitada", "extension-aceptada",
     "extension-rechazada", "reprogramacion-propuesta", "reprogramacion-rechazada",
     "fecha-devolucion-actualizada", "devolucion-registrada", "vencido", "finalizado",
     "cancelado", "cancelacion-rechazada", "periodo-liberado", "extension-retencion-solicitada",
     "extension-confirmacion-solicitada", "extension-retencion-cancelada", "recuperacion-pendiente"),
    ("PrestamoCreado", "ObjetoEntregado", "PrestamoActivado", "ExtensionSolicitada",
     "ExtensionAceptada", "ExtensionRechazada", "ReprogramacionPropuesta",
     "ReprogramacionRechazada", "FechaDevolucionActualizada", "DevolucionRegistrada",
     "PrestamoVencido", "PrestamoFinalizado", "PrestamoCancelado", "CancelacionRechazada",
     "PeriodoPrestamoLiberado", "ExtensionRetencionSolicitada", "ExtensionConfirmacionSolicitada",
     "ExtensionRetencionCancelada", "RecuperacionPendiente"),
))
ROUTES = {f"prestamos.{key}.v1": value for key, value in ROUTES.items()}
IDS = ("prestamo_id", "reserva_id", "publicacion_id", "prestamista_usuario_id", "prestatario_usuario_id")
# Only unambiguous lifecycle states; delivery/return registration are not state transitions here.
STATES = {"PrestamoCreado": "RESERVADO", "PrestamoActivado": "ACTIVO",
          "PrestamoVencido": "VENCIDO", "PrestamoFinalizado": "FINALIZADO",
          "PrestamoCancelado": "CANCELADO", "RecuperacionPendiente": "RECUPERACION_PENDIENTE"}


def validate_event(route, event):
    try:
        if not isinstance(event, dict) or ROUTES.get(route) != event["event_type"] or route not in ROUTES:
            raise ValueError("routing key mismatch")
        if type(event["event_version"]) is not int or event["event_version"] != 1:
            raise ValueError("unsupported event version")
        if type(event["aggregate_version"]) is not int or event["aggregate_version"] < 1:
            raise ValueError("invalid aggregate version")
        event = dict(event)
        event["event_id"] = str(UUID(event["event_id"]))
        event["aggregate_id"] = str(UUID(event["aggregate_id"]))
        if datetime.fromisoformat(event["occurred_at"].replace("Z", "+00:00")).tzinfo is None:
            raise ValueError("missing timezone")
        if not isinstance(event["correlation_id"], str) or len(event["correlation_id"]) > 100:
            raise ValueError("invalid correlation")
        payload = dict(event["payload"])
        for field in IDS:
            payload[field] = str(UUID(payload[field]))
        if payload["prestamo_id"] != event["aggregate_id"]:
            raise ValueError("aggregate mismatch")
        kind = event["event_type"]
        if kind == "PrestamoCreado":
            required = payload["garantia_requerida"]
            if type(required) is not bool:
                raise ValueError("invalid guarantee flag")
            amount = payload.get("garantia_monetaria_acordada")
            if required and amount is None:
                raise ValueError("missing agreed guarantee")
            amount = Decimal(str(amount)) if amount is not None else None
            if amount is not None and (not amount.is_finite() or amount < 0 or amount >= Decimal("10000000000")
                                       or amount != amount.quantize(Decimal(".01")) or required != (amount > 0)):
                raise ValueError("invalid guarantee amount")
            payload["garantia_monetaria_acordada"] = amount
            currency = payload["moneda"]
            if not isinstance(currency, str) or len(currency) != 3 or not currency.isascii() or not currency.isalpha() or currency != currency.upper():
                raise ValueError("invalid currency")
        date_key = "devolucion_original_en" if kind == "PrestamoCreado" else "devolucion_vigente_en"
        if kind in ("PrestamoCreado", "PrestamoActivado", "PrestamoVencido", "FechaDevolucionActualizada"):
            date = payload[date_key]
            if datetime.fromisoformat(date).tzinfo is not None or len(date) > 40:
                raise ValueError("invalid local return date")
        event["payload"] = payload
        return event
    except (KeyError, TypeError, AttributeError, ValueError, InvalidOperation) as exc:
        raise ValueError("invalid loan event") from exc


def projection_changes(row, event):
    p = event["payload"]
    kind, version = event["event_type"], event["aggregate_version"]
    if any(row[field] != p[field] for field in IDS):
        raise ValueError("loan identity changed")
    changes = {}
    if version > row["aggregate_version"]:
        changes.update(aggregate_version=version, last_event_type=kind)
    if kind in STATES and version > row["state_version"]:
        changes.update(estado=STATES[kind], state_version=version)
    if kind == "PrestamoCreado" and version > row["creation_version"]:
        changes.update(creation_version=version, garantia_requerida=p["garantia_requerida"],
                       garantia_monetaria_acordada=p["garantia_monetaria_acordada"], moneda=p["moneda"])
    if kind in ("PrestamoCreado", "PrestamoActivado", "PrestamoVencido", "FechaDevolucionActualizada") and version > row["date_version"]:
        changes.update(date_version=version, devolucion_vigente_en=p["devolucion_original_en" if kind == "PrestamoCreado" else "devolucion_vigente_en"])
    return changes

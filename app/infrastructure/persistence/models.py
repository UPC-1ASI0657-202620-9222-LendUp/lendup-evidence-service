"""Persistence mappings for the Evidence and Incident bounded context."""
from sqlalchemy import (
    CHAR, JSON, Column, ForeignKey, Index, MetaData, Numeric, Integer, Boolean, UniqueConstraint,
    String, Table, Text, text,
)
from sqlalchemy.dialects.mysql import DATETIME

metadata = MetaData()
timestamp = text("CURRENT_TIMESTAMP(6)")
options = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}

incident_closures = Table(
    "cierres_incidencias", metadata,
    Column("prestamo_id", CHAR(36), primary_key=True),
    Column("sellado", Boolean, nullable=False, server_default=text("0")),
    Column("sello_id", CHAR(36)),
    **options,
)

incidents = Table(
    "incidencias", metadata,
    Column("id", CHAR(36), primary_key=True),
    Column("prestamo_id", CHAR(36), nullable=False),
    Column("reportada_por_usuario_id", CHAR(36), nullable=False),
    Column("tipo", String(24), nullable=False),
    Column("descripcion", Text, nullable=False),
    Column("estado", String(20), nullable=False, server_default="PENDIENTE"),
    Column("reportada_en", DATETIME(fsp=6), nullable=False, server_default=timestamp),
    Column("revision_iniciada_en", DATETIME(fsp=6)),
    Column("resuelta_en", DATETIME(fsp=6)),
    Column("resuelta_por_usuario_id", CHAR(36)),
    Column("justificacion_resolucion", Text),
    Column("decision_garantia", String(24)),
    Column("monto_garantia_afectado", Numeric(12, 2)),
    Column("saldo_garantia_previsto", Numeric(12, 2)),
    Column("moneda", CHAR(3)),
    Column("actualizada_en", DATETIME(fsp=6), nullable=False, server_default=timestamp),
    Index("idx_incidencias_0", "estado", "tipo", "reportada_en"),
    Index("idx_incidencias_1", "prestamo_id", "estado"),
    **options,
)
evidence = Table(
    "evidencias", metadata,
    Column("id", CHAR(36), primary_key=True),
    Column("prestamo_id", CHAR(36), nullable=False),
    Column("incidencia_id", CHAR(36), ForeignKey("incidencias.id", name="fk_evidencias_incidencia_id", ondelete="RESTRICT")),
    Column("registrada_por_usuario_id", CHAR(36), nullable=False),
    Column("etapa", String(20), nullable=False),
    Column("tipo", String(20), nullable=False),
    Column("url", Text),
    Column("cloudinary_public_id", String(255)),
    Column("observacion", Text),
    Column("registrada_en", DATETIME(fsp=6), nullable=False, server_default=timestamp),
    Column("estado_integracion", String(24), nullable=False, server_default="PENDIENTE"),
    Index("idx_evidencias_0", "prestamo_id", "etapa", "registrada_en"),
    Index("idx_evidencias_1", "incidencia_id"),
    **options,
)
analyses = Table(
    "analisis_evidencias", metadata,
    Column("id", CHAR(36), primary_key=True),
    Column("prestamo_id", CHAR(36), nullable=False),
    Column("incidencia_id", CHAR(36), ForeignKey("incidencias.id", name="fk_analisis_evidencias_incidencia_id", ondelete="RESTRICT")),
    Column("evidencia_inicial_id", CHAR(36), ForeignKey("evidencias.id", name="fk_analisis_evidencias_evidencia_inicial_id", ondelete="RESTRICT"), nullable=False),
    Column("evidencia_final_id", CHAR(36), ForeignKey("evidencias.id", name="fk_analisis_evidencias_evidencia_final_id", ondelete="RESTRICT"), nullable=False),
    Column("solicitado_por_usuario_id", CHAR(36), nullable=False),
    Column("estado", String(20), nullable=False, server_default="PENDIENTE"),
    Column("solicitado_en", DATETIME(fsp=6), nullable=False, server_default=timestamp),
    Column("completado_en", DATETIME(fsp=6)),
    Column("resultado_resumen", Text),
    Column("resultado_detalle", JSON),
    Column("error_descripcion", Text),
    Index("idx_analisis_evidencias_0", "prestamo_id", "solicitado_en"),
    Index("idx_analisis_evidencias_1", "incidencia_id"),
    **options,
)
incident_notes = Table(
    "observaciones_incidencia", metadata,
    Column("id", CHAR(36), primary_key=True),
    Column("incidencia_id", CHAR(36), ForeignKey("incidencias.id", name="fk_observaciones_incidencia_incidencia_id", ondelete="RESTRICT"), nullable=False),
    Column("administrador_usuario_id", CHAR(36), nullable=False),
    Column("contenido", Text, nullable=False),
    Column("registrada_en", DATETIME(fsp=6), nullable=False, server_default=timestamp),
    Index("idx_observaciones_incidencia_0", "incidencia_id", "registrada_en"),
    **options,
)


outbox_events = Table(
    "outbox_events", metadata,
    Column("id", CHAR(36), primary_key=True),
    Column("aggregate_id", CHAR(36), nullable=False),
    Column("aggregate_version", Integer, nullable=False),
    Column("routing_key", String(150), nullable=False),
    Column("envelope", JSON, nullable=False),
    Column("mandatory", Boolean, nullable=False),
    Column("created_at", DATETIME(fsp=6), nullable=False),
    Column("next_attempt_at", DATETIME(fsp=6), nullable=False),
    Column("published_at", DATETIME(fsp=6)),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("last_error", String(255)),
    UniqueConstraint("aggregate_id", "aggregate_version", name="uq_outbox_aggregate_version"),
    Index("idx_outbox_pending", "published_at", "next_attempt_at"),
    **options,
)


inbox_events = Table(
    "inbox_events", metadata,
    Column("id", CHAR(36), primary_key=True),
    Column("aggregate_id", CHAR(36), nullable=False),
    Column("aggregate_version", Integer, nullable=False),
    Column("routing_key", String(150), nullable=False),
    Column("processed_at", DATETIME(fsp=6), nullable=False, server_default=timestamp),
    **options,
)

loan_projection = Table(
    "loan_projection", metadata,
    Column("prestamo_id", CHAR(36), primary_key=True),
    Column("reserva_id", CHAR(36), nullable=False),
    Column("publicacion_id", CHAR(36), nullable=False),
    Column("prestamista_usuario_id", CHAR(36), nullable=False),
    Column("prestatario_usuario_id", CHAR(36), nullable=False),
    Column("aggregate_version", Integer, nullable=False, server_default="0"),
    Column("last_event_type", String(64)),
    Column("estado", String(24)),
    Column("state_version", Integer, nullable=False, server_default="0"),
    Column("creation_version", Integer, nullable=False, server_default="0"),
    Column("garantia_requerida", Boolean),
    Column("garantia_monetaria_acordada", Numeric(12, 2)),
    Column("moneda", CHAR(3)),
    Column("devolucion_vigente_en", String(40)),
    Column("date_version", Integer, nullable=False, server_default="0"),
    **options,
)

# Evidence integration events v1

Exchange durable topic: lendup.domain.events. Envelope: event_id UUID, event_type, event_version=1, aggregate_version, aggregate_id UUID, occurred_at UTC, correlation_id UUID, payload. The routing keys and mandatory payload fields for incidents match the consumed-events contracts in Loans, Payments and Notifications main, inspected before implementation.

| Event | Routing key | Aggregate | Consumers |
|---|---|---|---|
| EvidenciaRegistrada | evidencias.evidencia-registrada.v1 | evidence UUID, version 1 | informational; no verified consumer yet |
| IncidenciaReportada | evidencias.incidencia-reportada.v1 | incident UUID, version 1 | Loans, Payments, Notifications |
| IncidenciaResuelta | evidencias.incidencia-resuelta.v1 | incident UUID, version 2 | Loans, Payments, Notifications |

Both incident events include incidencia_id, prestamo_id, prestamista_usuario_id and prestatario_usuario_id. Resolved adds decision_garantia, monto_garantia_afectado (JSON number), moneda and justificacion_resolucion. Evidence events exclude media URLs and observation contents. They are emitted for completed evidence, including incident attachments/notes and statements, not unverified placeholders.

Each event is inserted into outbox_events in the same transaction as its business record. Apply Alembic revision 0002_event_outbox before creating new records. OUTBOX_PUBLISHER_ENABLED=false by default; set true and configure RABBITMQ_URL to start the relay with FastAPI. It retries pending events using bounded exponential backoff (2–300 seconds), persistent AMQP messages and publisher confirms. Incident events use mandatory=true; unbound routes remain pending. Informational evidence events may be confirmed even without a consumer. MySQL row locking prevents concurrent publishing of the same row and unresolved predecessor versions block later versions of the same aggregate. Cross-aggregate ordering is not guaranteed.

Delivery is at least once: broker confirmation followed by a database failure can cause duplicates with the same event_id. Consumers must deduplicate. Mandatory confirms only at least one binding, not that all three intended services received or processed a message. Declare real consumer queues before enabling publishing; avoid debug queues on shared brokers because they can mask missing consumers. A broker outage is not a business transaction rollback. Pending events are retried indefinitely; monitor attempts and last_error.

The administrative loan contract must include both participant IDs to publish the resolved event. This contract is not yet present on Loans main. No consumer or financial workflow was changed in other repositories. The Loans team also requests consuming prestamos.* for a local projection; that consumer is not implemented here. Existing incidents created before migration need reconciliation, not automatic replay. End-to-end testing, financial consistency, DLQ handling on consumer side, retention policy and production monitoring remain pending.

For local testing use an isolated RabbitMQ broker and test-only records. Do not enable publication against the team's shared broker without coordinating queues, data and payment side effects.

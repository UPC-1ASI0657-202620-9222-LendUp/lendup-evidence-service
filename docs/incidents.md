# Participant incident management

POST /api/v1/incidencias accepts JSON (prestamo_id, tipo, descripcion, optional observaciones and clave_idempotencia UUID) or multipart (reporte JSON, repeated fotos). Photos are validated, limited to six and 5 MiB each, and stored in Cloudinary under lendup/incidencias. POST returns 201. The idempotency key identifies the report by loan, reporter, type and description; retries return existing attachments rather than replacing them.

GET /api/v1/incidencias and GET /api/v1/incidencias/{id} use the authoritative participant-only Loans API. The current list implementation checks each distinct loan referenced by local incidents; optimize with a participant loan-list contract before production scale. The response includes the loan and locally owned evidence and notes. Reservation details are not yet included because there is no verified reservation contract in this service.

POST /api/v1/incidencias/{id}/descargo accepts contenido (20–10000 characters); only the counterparty may submit once, and resolved incidents reject statements. The incident row is locked for concurrent statements; future admin routes must follow the same locking strategy.

No cross-service database reads or writes. Notifications and Loans pending-incident counts are not yet updated: RabbitMQ integration is pending. Loan state is validated remotely, not atomically with the local write. Admin access and resolution are pending. Cloudinary uploads are compensated on pre-commit errors; ambiguous commit failures require reconciliation. Request-size limits at the gateway, real integration tests and data migration remain pending.

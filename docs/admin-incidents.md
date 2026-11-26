# Administrative incident management

Four routes under /api/v1/admin/incidencias: GET list (estado/tipo filters), POST /{id}/revision, POST /{id}/observaciones and POST /{id}/resolucion. Every route verifies Firebase and the persisted role through Identity GET /internal/v1/identidad/usuarios/{usuarioId}/rol using IDENTITY_SERVICE_TOKEN. Only ADMINISTRADOR is accepted. Role lookup failure denies access.

List, review and notes use locally owned incident, evidence and note data. They do not expose a fabricated loan or reservation object. Review is idempotent; notes and resolution require EN_REVISION. RESUELTA is terminal. Row locks serialize changes and statements. Resolution locks the incidents of the same loan before calculating the remaining agreed guarantee, rejects invalid money or inconsistent decisions, and records the admin, justification, currency and planned balance. It does not execute payment operations.

## Pending cross-service contract

Loans main currently exposes participant-only detail and an internal contact-access route. The following is a PROPOSAL, not a deployed endpoint:

GET /internal/v1/prestamos/{id}/incidencias
Authorization: Bearer <dedicated evidence service token>

Required JSON fields: id (loan UUID), garantia_monetaria_acordada (decimal amount, including explicit zero), moneda (three-letter ISO currency), prestamista_usuario_id and prestatario_usuario_id (UUIDs, required for event recipients). The Loans team must restrict this route to Evidence and keep it off the public gateway. Configure LOANS_SERVICE_URL and LOANS_SERVICE_TOKEN only after agreement. Missing configuration, missing route, invalid amount or unavailable service returns 503 and no resolution is persisted. Even SIN_AFECTACION requires authoritative financial context.

Admin list currently contains local evidence (including evidencias_prestamo), not the full loan/reservation enrichment of the monolith. Integration with Loans and Payments must reconcile existing guarantee decisions and prevent cross-service races; local row locking is not a distributed transaction. Do not enable real financial workflows until this integration and historical-data migration are verified. Incident resolution now queues an outbox event; real notification and loan/payment consumption remain unverified.

No schema changes required.

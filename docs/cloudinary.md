# Cloudinary
Use CLOUDINARY_ENABLED=true and CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET in your private .env. Do not commit credentials. Dynamic asset folders lendup/evidencias/entrega and lendup/evidencias/devolucion are explicit; public IDs include loan and upload UUID. Incident uploads are a separate pending use case.

POST /api/v1/prestamos/{id}/evidencias accepts JSON or multipart (etapa, uploadId UUID, file). Max 5 MiB, six media records per stage. The MySQL advisory lock serializes multipart writes per loan and stage. JSON placeholders currently do not share this lock; full cross-path quota enforcement is pending. Request body limits should also be configured at the gateway. On uncertain database failure the deterministic asset is retained for reconciliation/retry rather than risking deletion of committed evidence. Cleanup adapter is available, automatic reconciliation is pending.

Run pytest and alembic upgrade head against a dedicated MySQL database, then test with a participant Firebase token and a real loan. Use restricted credentials for production; do not use Root in AWS.

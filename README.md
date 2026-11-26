# LendUp Evidence and Incident Service

FastAPI service for evidence registration, incident reporting and review, guarantee decisions, and assisted image comparison.

## Local execution

```powershell
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --port 8000
python -m pytest -q
```

Set `DATABASE_URL` to the service's `mysql+pymysql` schema URL before running Alembic and the API. See `.env.example` for integration settings. The E2E Compose file provisions the schema and calls Alembic on the existing MySQL volume.

## Service contracts

- Public routes use Firebase ID tokens with email verification and revocation checks. Identidad resolves the UID and supplies the persisted administrative role. Set `IDENTITY_SERVICE_TOKEN` to the corresponding `IDENTITY_EVIDENCE_SERVICE_TOKEN`.
- Set `LOANS_SERVICE_TOKEN` to `LOANS_EVIDENCE_SERVICE_TOKEN` for participant context and the agreed loan guarantee. A missing agreed amount prevents a guarantee decision.
- Set `RESERVATIONS_SERVICE_URL` and `RESERVATIONS_SERVICE_TOKEN` to query the accepted agreement. Reservas authorizes only `GET /internal/v1/reservas/{id}/acuerdo` with `RESERVATIONS_EVIDENCE_SERVICE_TOKEN`. The incident detail and administrative list present the snapshot under `reserva`.
- Préstamos sends `EVIDENCE_LOANS_SERVICE_TOKEN` to `POST /internal/v1/prestamos/{id}/cierre-incidencias`. Evidencias serializes admission and closure in MySQL and returns the resolved IDs. Every closure attempt stores a new seal ID. A report against an existing seal can check the committed loan state through `GET /internal/v1/prestamos/{id}/admision-incidencias`. It releases its local lock before this check and only removes the seal it observed if Préstamos is still open.
- Enable `OUTBOX_PUBLISHER_ENABLED` and `LOAN_CONSUMER_ENABLED` with `RABBITMQ_URL` to use the shared `lendup.domain.events` exchange. Event schemas and examples are under `contracts/events/v1`.
- Cloudinary stores verified uploads. Gemini supplies assisted comparison through a circuit breaker. The E2E environment replaces these providers with test doubles.

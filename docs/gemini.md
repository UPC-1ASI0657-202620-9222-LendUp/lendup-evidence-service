# Assisted evidence analysis

Set GEMINI_API_KEY and GEMINI_MODEL to a model enabled for image input and structured JSON output in your Gemini API account. Never commit the key. GEMINI_TIMEOUT_SECONDS defaults to 20 and is capped at 20 for the combined downloads and model request.

POST /api/v1/prestamos/{id}/analisis-evidencias accepts evidencia_inicial_id, evidencia_final_id and optional incidencia_id. The caller must be a loan participant. Both photos must be verified uploads for that loan, first ENTREGA then DEVOLUCION. Returns 201 and a persisted PENDIENTE analysis. GET /api/v1/prestamos/{id}/analisis-evidencias/{analisis_id} allows participants to poll the result. This GET is an additive contract beyond the monolith.

The background task claims PENDIENTE atomically, downloads only HTTPS images in the configured Cloudinary cloud (no redirects, max 5 MiB per image), calls Gemini using google-genai and validates structured output. States: PENDIENTE, PROCESANDO, COMPLETADO, FALLIDO. Failures are recorded without changing loans, incidents or guarantees. The result is advisory and explicitly requires human review.

FastAPI BackgroundTasks is an interim in-process mechanism; a process restart may leave jobs pending or processing. A process-local circuit breaker is implemented (see docs/circuit-breaker.md). Durable execution/recovery, rate limits, deduplication of repeated requests, production privacy review, and RabbitMQ are pending. Do not send real personal information in test photos; review provider data handling before production use. No schema changes.

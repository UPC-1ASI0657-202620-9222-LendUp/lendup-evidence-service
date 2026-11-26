# Integration status

Firebase ID token verification uses ADC and FIREBASE_PROJECT_ID. The verified UID is mapped to the LendUp UUID via Identity. Identity main now exposes the Evidence-authorized UID and role endpoints. Configure IDENTITY_SERVICE_URL and IDENTITY_SERVICE_TOKEN (dedicated token of at least 32 characters). Live deployment and credentials still require verification.

Loans participant operations use its existing GET /api/v1/prestamos/{id} with the verified user's token. Administrative resolution requires a proposed private contract, documented in docs/admin-incidents.md; it is not available on Loans main at this time and fails closed. Admin list, review and notes use only owned data.

Evidence registration, multipart Cloudinary upload, participant incident management and administrative routes are implemented. The existing 29 automated tests passed locally. A real Gemini text generation succeeded with the developer's personal project. Real image comparison and structured output remain unverified. Circuit breaker implemented; new tests require execution. Real upload, integrated requests, physical migration verification, historical-data migration, durable analysis execution, distributed circuit coordination, messaging, full response compatibility and deployment remain pending.

Keep service-to-service routes private and use TLS. Do not commit ADC files or tokens.

# Integration status

Firebase ID token verification uses ADC and FIREBASE_PROJECT_ID. The verified Firebase UID must be resolved to the LendUp user UUID; never use the UID directly as a domain user ID.

Identity currently allows only reservations, payments and notifications on GET /internal/v1/identidad/firebase/{uid}. Its team must add an evidence-specific token and permission to this route. Configure IDENTITY_SERVICE_URL and IDENTITY_SERVICE_TOKEN here after that change. Tokens must be distinct and at least 32 characters.

Loans uses the existing participant-only GET /api/v1/prestamos/{id} contract, forwarding the verified user's Bearer token. Configure LOANS_SERVICE_URL. The dedicated internal loan contract is not assumed to exist. Admin authorization will require an authoritative Identity role contract; never trust a user-supplied role.

Current evidence registration supports observations and pending media placeholders. External media URLs are deliberately not trusted as evidence; verified multipart upload with Cloudinary remains to be implemented. This is not yet full monolith compatibility. Analysis, incidents, messaging and admin routes remain pending.

Keep service-to-service routes private and use TLS. Do not commit ADC files or tokens.

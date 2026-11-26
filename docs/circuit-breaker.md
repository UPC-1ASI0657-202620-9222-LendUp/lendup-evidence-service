# Gemini circuit breaker

The Google AI Adapter shares a process-local circuit breaker. Three consecutive counted failures open the circuit for 60 seconds. While open, calls fail immediately without contacting Gemini or downloading Cloudinary images. After cooldown one half-open probe is admitted; success closes the circuit, failure/cancellation reopens it. Generation tokens prevent stale in-flight completions from changing newer circuit state. The combined download and model request timeout is configurable up to 60 seconds, with a default of 60 seconds.

Counted failures: timeouts, transport errors, provider 401/403/429/5xx, and invalid model output. Cloudinary transport/HTTP failures during the combined comparison also count when classified as transient/authorization errors; invalid local URLs and invalid image bytes do not. No automatic retries are added. The service saves FALLIDO with an advisory message when the circuit is open; loans, incidents and guarantees are unchanged.

The state is shared within one Python process only, resets on restart and is not distributed across ECS replicas. Durable job execution/recovery, provider-specific metrics, production rate limiting and cross-replica coordination remain pending. Defaults are fixed at 3 failures and 60 seconds for the initial architecture; no database migration or secrets change is required.

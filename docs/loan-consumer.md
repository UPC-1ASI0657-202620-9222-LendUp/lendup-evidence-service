# Loans subscription v1

Enable with LOAN_CONSUMER_ENABLED=true and RABBITMQ_URL. Apply Alembic 0003 first.
The durable queue evidence.events.v1 binds prestamos.*.v1 on the shared topic exchange.
Rejected messages go to evidence.events.v1.dlq via the shared topic DLX. Operational database errors receive three attempts per delivery. Other errors are dead-lettered; inspect and replay manually after fixing the cause. Classic queue DLX delivery is not guaranteed if the destination is unavailable.
The inbox primary key deduplicates event_id in the same transaction as the projection; ACK follows commit. Projection versions independently protect lifecycle state, agreed guarantee and return date against late events. A projection without PrestamoCreado has unknown guarantee, not zero. Only fields used by the projection are validated, not the entire producer schema.
Loan REST validation remains authoritative; this projection is not used for permissions or money decisions. No historical replay is automatic: declare queues before producers publish, and coordinate backfill with Loans for older loans. No change to teammate services.

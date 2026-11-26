# Evidence database

Create a dedicated empty MySQL database and a dedicated database user with access only to it. Set DATABASE_URL in the local .env file (never commit credentials).

Example format: mysql+pymysql://evidence_user:password@localhost:3306/lendup_evidence?charset=utf8mb4

Run from the repository root:

```bash
python -m alembic upgrade head
python -m alembic current
python -m pytest -q
```

The initial revision preserves the four table definitions from lendup-backend/src/main/resources/schema.sql. Loan and user IDs are external references, not cross-service foreign keys. Repository adapters do not commit; application use cases must commit or roll back their transactions.

This migration creates schema only; it does not copy existing monolith data. Plan data migration and reconciliation before switching live routes. Downgrade drops the four tables and destroys their contents; do not run it on a populated database without backup.

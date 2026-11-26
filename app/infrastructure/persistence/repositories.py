from typing import Any
from uuid import uuid4

from sqlalchemy import Table, insert, select, update
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import analyses, evidence, incidents, incident_notes


class SqlRecordRepository:
    """Use-case controlled transactions; only trusted domain data goes here."""

    def __init__(self, session: Session, table: Table):
        self.session = session
        self.table = table

    def get(self, record_id: str) -> dict[str, Any] | None:
        row = self.session.execute(
            select(self.table).where(self.table.c.id == record_id)
        ).mappings().one_or_none()
        return dict(row) if row is not None else None

    def add(self, values: dict[str, Any]) -> dict[str, Any]:
        data = dict(values)
        data.setdefault("id", str(uuid4()))
        self.session.execute(insert(self.table).values(**data))
        record = self.get(data["id"])
        if record is None:
            raise RuntimeError("Inserted record could not be read")
        return record

    def update(self, record_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        if "id" in values:
            raise ValueError("Record IDs are immutable")
        self.session.execute(update(self.table).where(self.table.c.id == record_id).values(**values))
        return self.get(record_id)

    def list_by(self, **filters: Any) -> list[dict[str, Any]]:
        stmt = select(self.table).filter_by(**filters)
        return [dict(row) for row in self.session.execute(stmt).mappings()]


class EvidenceRepository(SqlRecordRepository):
    def __init__(self, session: Session):
        super().__init__(session, evidence)


class IncidentRepository(SqlRecordRepository):
    def __init__(self, session: Session):
        super().__init__(session, incidents)


class AnalysisRepository(SqlRecordRepository):
    def __init__(self, session: Session):
        super().__init__(session, analyses)


class IncidentNoteRepository(SqlRecordRepository):
    def __init__(self, session: Session):
        super().__init__(session, incident_notes)

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.infrastructure.persistence.models import metadata


def test_only_owned_tables():
    assert set(metadata.tables) == {
        "incidencias", "evidencias", "analisis_evidencias", "observaciones_incidencia"
    }
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.column.table.name in metadata.tables


def test_mysql_ddl_compiles():
    for table in metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=mysql.dialect()))
        assert "CREATE TABLE" in ddl
        assert "utf8mb4" in ddl

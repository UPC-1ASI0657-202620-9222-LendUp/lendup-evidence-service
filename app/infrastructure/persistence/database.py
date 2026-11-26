from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.shared.config import Settings


def database_url() -> str:
    url = Settings().database_url
    if not url or make_url(url).drivername != "mysql+pymysql":
        raise RuntimeError("Set DATABASE_URL to a mysql+pymysql connection URL")
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True, pool_recycle=1800)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise

"""Create the local schema.

``alembic`` is declared as an optional dependency for full migrations; this
helper keeps first-run bootstrap deterministic when Alembic is not installed.
"""

from __future__ import annotations

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url

from engine.db.models import Base


def init_schema(db_url: str = "sqlite:///aisounder.db") -> Engine:
    url = make_url(db_url)
    connect_args = {"check_same_thread": False} if url.get_backend_name() == "sqlite" else {}
    engine = create_engine(db_url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


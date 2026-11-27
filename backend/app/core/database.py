"""Koneksi SQLAlchemy, sesi database, dan inisialisasi skema Supabase PostgreSQL."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _build_engine():
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
    )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Buat tabel yang belum ada dan tambahkan kolom aditif pada skema PostgreSQL."""
    from app.models import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if engine.dialect.name == "postgresql":
        additive_migrations = [
            "ALTER TABLE alley_segments ADD COLUMN IF NOT EXISTS pin_point JSONB",
            "ALTER TABLE cycle_ranking_results ADD COLUMN IF NOT EXISTS normalized_values JSONB",
            "ALTER TABLE cycle_ranking_results ADD COLUMN IF NOT EXISTS weighted_values JSONB",
        ]
        with engine.begin() as conn:
            for ddl in additive_migrations:
                conn.execute(text(ddl))

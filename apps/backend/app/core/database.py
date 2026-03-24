from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.resolved_database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


def init_db() -> None:
    from app import models  # noqa: F401

    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _run_sqlite_migrations()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_sqlite_migrations() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(user_preferences)"))
        }
        if "bilibili_cookie" not in columns:
            connection.execute(
                text("ALTER TABLE user_preferences ADD COLUMN bilibili_cookie TEXT NOT NULL DEFAULT ''")
            )
        if "download_output_dir" not in columns:
            connection.execute(
                text("ALTER TABLE user_preferences ADD COLUMN download_output_dir TEXT NOT NULL DEFAULT './data/downloads'")
            )

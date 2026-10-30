import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def session_factory(url: str | None = None) -> sessionmaker:
    engine = create_engine(
        url or os.environ["DATABASE_URL"],
        pool_pre_ping=True,
        pool_size=int(os.environ.get("DB_POOL_SIZE", "10")),
        max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "20")),
    )
    return sessionmaker(bind=engine, expire_on_commit=False)

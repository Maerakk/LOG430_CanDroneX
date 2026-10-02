import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://candronex:candronex@127.0.0.1:3310")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionFactory = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass
from sqlalchemy.orm import sessionmaker

from app.database.engine import engine

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

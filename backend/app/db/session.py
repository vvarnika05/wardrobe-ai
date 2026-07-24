from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#autocommit=False: This means that changes made to the database within a session will not be automatically committed. You need to explicitly call db.commit() to save changes.
#autoflush=False: This means that changes made to the database within a session will not be automatically flushed to the database. You need to explicitly call db.flush() to send changes to the database.

#sessionmaker: This is a factory for creating new Session objects. It is configured with the engine and the autocommit and autoflush settings.
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        #every session opened should be closed


# Browser
#    │
#    ▼
# FastAPI
#    │
#    ▼
# Need database?
#    │
#    ▼
# get_db()
#    │
#    ▼
# Creates a database session
#    │
#    ▼
# Route uses the session
#    │
#    ▼
# Session closed

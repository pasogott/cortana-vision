import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/snapshot.db")

# Convert to absolute path inside container
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    # Ensure absolute path inside /app
    if not db_path.startswith("/"):
        db_path = os.path.join("/app", db_path)
        DATABASE_URL = f"sqlite:///{db_path}"

    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Initialize database tables."""
    from app import models
    Base.metadata.create_all(bind=engine)

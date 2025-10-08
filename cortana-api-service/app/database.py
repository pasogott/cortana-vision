from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/snapshot.db")

# Set up database connection
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def init_db():
    """Create or upgrade SQLite schema automatically."""
    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)

    print("[INIT] Database schema ensured and upgraded.")

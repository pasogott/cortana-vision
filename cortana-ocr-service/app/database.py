from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
import sqlite3

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def init_db():
    Base.metadata.create_all(bind=engine)

def run_all():
    conn = sqlite3.connect(settings.database_url.replace("sqlite:///", ""))
    cur = conn.cursor()
    # Drop legacy triggers once
    cur.executescript("""
        DROP TRIGGER IF EXISTS ocr_ai;
        DROP TRIGGER IF EXISTS ocr_ad;
        DROP TRIGGER IF EXISTS ocr_au;
    """)
    conn.commit()
    conn.close()
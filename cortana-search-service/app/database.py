from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from app.database_setup import run_all

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/snapshot.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    try:
        with engine.connect() as conn:
            print("[SEARCH][DB] Connected to snapshot.db ✅")
        run_all()
        print("[SEARCH][DB] Schema migration checks complete ✅")
    except Exception as e:
        print(f"[SEARCH][DB][ERR] Could not connect or migrate → {e}")

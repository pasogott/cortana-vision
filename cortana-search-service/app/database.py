from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Point to shared snapshot.db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/data/snapshot.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Do not re-create tables; just ensure DB is reachable
    try:
        with engine.connect() as conn:
            print("[SEARCH][DB] Connected to snapshot.db ✅")
    except Exception as e:
        print(f"[SEARCH][DB][ERR] Could not connect → {e}")

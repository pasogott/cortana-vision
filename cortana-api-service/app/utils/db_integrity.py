import sqlite3
from app.config import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")

def ensure_integrity():
    """
    Permanent self-healing schema verification:
    - Ensures all required tables exist (videos, frames, ocr_frames)
    - Repairs missing foreign key parents
    - Creates missing columns if schema evolves
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --------------------------
    # 1. Ensure core tables
    # --------------------------
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS videos (
        id VARCHAR PRIMARY KEY,
        filename VARCHAR NOT NULL,
        path VARCHAR,
        is_processed BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR DEFAULT 'queued'
    );

    CREATE TABLE IF NOT EXISTS frames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id VARCHAR NOT NULL,
        frame_path VARCHAR UNIQUE,
        greyscale_is_processed BOOLEAN DEFAULT 0,
        FOREIGN KEY(video_id) REFERENCES videos(id)
    );

    CREATE TABLE IF NOT EXISTS ocr_frames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id VARCHAR NOT NULL,
        frame_path VARCHAR UNIQUE,
        ocr_text TEXT,
        is_processed BOOLEAN DEFAULT 0,
        FOREIGN KEY(video_id) REFERENCES videos(id)
    );
    """)

    # --------------------------
    # 2. Ensure columns (schema drift fix)
    # --------------------------
    columns = {
        "videos": ["id", "filename", "is_processed", "status"],
        "ocr_frames": ["ocr_text", "frame_path", "is_processed"]
    }

    for table, required_cols in columns.items():
        cur.execute(f"PRAGMA table_info({table});")
        existing = [row[1] for row in cur.fetchall()]
        for col in required_cols:
            if col not in existing:
                print(f"[DB][FIX] Adding missing column '{col}' to {table}…")
                if col == "status":
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN status VARCHAR DEFAULT 'queued';")
                elif col == "ocr_text":
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN ocr_text TEXT;")
                elif col == "is_processed":
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN is_processed BOOLEAN DEFAULT 0;")
                conn.commit()

    conn.commit()
    conn.close()
    print("[DB][HEAL] ✅ Database schema integrity verified & repaired.")

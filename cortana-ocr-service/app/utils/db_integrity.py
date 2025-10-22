# app/utils/db_integrity.py
import os
import sqlite3
from app.config import settings

# Use the env-driven name (UPPERCASE) to avoid AttributeError
DB_PATH = settings.database_url.replace("sqlite:///", "")

def ensure_integrity():
    """
    Permanent startup-time repair system.
    - Ensures core tables exist
    - Adds missing columns (schema drift)
    - Ensures FTS virtual table + triggers
    - Heals missing parent videos for frames/ocr_frames
    - PRAGMA toggles for correctness
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")      # enforce FK constraints deterministically
    conn.execute("PRAGMA journal_mode=WAL;")     # better concurrency
    cur = conn.cursor()

    # 1) Core tables (idempotent)
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

    # 2) Schema drift: ensure columns exist
    def _ensure_col(table, name, decl):
        cur.execute(f"PRAGMA table_info({table});")
        have = {r[1] for r in cur.fetchall()}
        if name not in have:
            print(f"[DB][AUTOFIX] Adding column {table}.{name}")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl};")

    _ensure_col("videos", "status", "VARCHAR DEFAULT 'queued'")
    _ensure_col("videos", "is_processed", "BOOLEAN DEFAULT 0")
    _ensure_col("videos", "path", "VARCHAR")

    _ensure_col("frames", "greyscale_is_processed", "BOOLEAN DEFAULT 0")

    _ensure_col("ocr_frames", "ocr_text", "TEXT")
    _ensure_col("ocr_frames", "is_processed", "BOOLEAN DEFAULT 0")

    # 3) FTS + triggers (idempotent)
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS ocr_index
        USING fts5(video_id, frame_path, ocr_text);
    """)

    cur.executescript("""
        DROP TRIGGER IF EXISTS ocr_frames_ai;
        CREATE TRIGGER IF NOT EXISTS ocr_frames_ai
        AFTER INSERT ON ocr_frames
        BEGIN
            INSERT INTO ocr_index(video_id, frame_path, ocr_text)
            VALUES (new.video_id, new.frame_path, new.ocr_text);
        END;

        DROP TRIGGER IF EXISTS ocr_frames_au;
        CREATE TRIGGER IF NOT EXISTS ocr_frames_au
        AFTER UPDATE ON ocr_frames
        BEGIN
            UPDATE ocr_index
            SET ocr_text = new.ocr_text
            WHERE frame_path = old.frame_path;
        END;

        DROP TRIGGER IF EXISTS ocr_frames_ad;
        CREATE TRIGGER IF NOT EXISTS ocr_frames_ad
        AFTER DELETE ON ocr_frames
        BEGIN
            DELETE FROM ocr_index WHERE frame_path = old.frame_path;
        END;
    """)

    # 4) Heal missing parent videos to satisfy FK on insert
    cur.execute("""
        INSERT INTO videos (id, filename, status)
        SELECT DISTINCT f.video_id, 'auto_recovered.mp4', 'processing'
        FROM frames f
        WHERE f.video_id NOT IN (SELECT id FROM videos);
    """)
    cur.execute("""
        INSERT INTO videos (id, filename, status)
        SELECT DISTINCT o.video_id, 'auto_recovered.mp4', 'processing'
        FROM ocr_frames o
        WHERE o.video_id NOT IN (SELECT id FROM videos);
    """)

    conn.commit()
    conn.close()
    print("[DB][SELFHEAL] ✅ Schema, FTS, triggers, and parent integrity verified.")

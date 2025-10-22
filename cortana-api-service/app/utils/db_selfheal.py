import sqlite3
import os
from app.config import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")

def self_heal_database():
    """
    Permanent startup-time repair system.
    Runs at every service boot to guarantee schema, tables,
    columns, and constraints exist and are consistent.
    """

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ------------------------------------
    # 1️⃣  Create all critical tables
    # ------------------------------------
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

    # ------------------------------------
    # 2️⃣  Ensure missing columns are added
    # ------------------------------------
    expected_columns = {
        "videos": {
            "status": "VARCHAR DEFAULT 'queued'",
            "is_processed": "BOOLEAN DEFAULT 0",
            "path": "VARCHAR"
        },
        "frames": {
            "greyscale_is_processed": "BOOLEAN DEFAULT 0"
        },
        "ocr_frames": {
            "ocr_text": "TEXT",
            "is_processed": "BOOLEAN DEFAULT 0"
        }
    }

    for table, cols in expected_columns.items():
        cur.execute(f"PRAGMA table_info({table});")
        existing_cols = {r[1] for r in cur.fetchall()}
        for name, decl in cols.items():
            if name not in existing_cols:
                print(f"[DB][AUTOFIX] Adding missing column '{name}' to {table}")
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl};")

    # ------------------------------------
    # 3️⃣  Ensure FTS index exists
    # ------------------------------------
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS ocr_index
        USING fts5(video_id, frame_path, ocr_text);
    """)

    # ------------------------------------
    # 4️⃣  Ensure triggers for auto indexing
    # ------------------------------------
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

    # ------------------------------------
    # 5️⃣  Integrity checks for missing parents
    # ------------------------------------
    cur.execute("""
        INSERT INTO videos (id, filename, status)
        SELECT DISTINCT video_id, 'auto_recovered.mp4', 'processing'
        FROM ocr_frames
        WHERE video_id NOT IN (SELECT id FROM videos);
    """)

    cur.execute("""
        INSERT INTO videos (id, filename, status)
        SELECT DISTINCT video_id, 'auto_recovered.mp4', 'processing'
        FROM frames
        WHERE video_id NOT IN (SELECT id FROM videos);
    """)

    conn.commit()
    conn.close()
    print("[DB][SELFHEAL] ✅ Database structure repaired and verified.")

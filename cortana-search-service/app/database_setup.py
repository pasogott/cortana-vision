# app/database_setup.py
import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "sqlite:////app/data/snapshot.db").replace("sqlite:///", "")

def run_all():
    """
    Ensure base tables and FTS index exist and are consistent.
    Safe to call multiple times.
    """
    print("[SEARCH][DB_SETUP] Ensuring schema and FTS index...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # --- Core tables ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        id TEXT PRIMARY KEY,
        filename TEXT,
        path TEXT,
        is_processed BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'processing',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS frames (
        id TEXT PRIMARY KEY,
        video_id TEXT,
        frame_number INTEGER,
        frame_time FLOAT,
        path TEXT,
        greyscale_is_processed BOOLEAN DEFAULT 0,
        ocr_content TEXT,
        FOREIGN KEY(video_id) REFERENCES videos(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ocr_frames (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video_id TEXT,
        frame_path TEXT,
        ocr_text TEXT,
        is_processed BOOLEAN DEFAULT 0
    );
    """)

    # --- FTS index with correct column names ---
    cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS ocr_index
    USING fts5(
        video_id,
        frame_path,
        text,
        content='ocr_frames',
        content_rowid='id'
    );
    """)

    # --- Sync triggers to keep index fresh ---
    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS ocr_frames_ai AFTER INSERT ON ocr_frames
    BEGIN
        INSERT INTO ocr_index(rowid, video_id, frame_path, text)
        VALUES (new.id, new.video_id, new.frame_path, new.ocr_text);
    END;
    """)

    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS ocr_frames_au AFTER UPDATE ON ocr_frames
    BEGIN
        UPDATE ocr_index
        SET video_id = new.video_id,
            frame_path = new.frame_path,
            text = new.ocr_text
        WHERE rowid = new.id;
    END;
    """)

    cur.execute("""
    CREATE TRIGGER IF NOT EXISTS ocr_frames_ad AFTER DELETE ON ocr_frames
    BEGIN
        DELETE FROM ocr_index WHERE rowid = old.id;
    END;
    """)

    conn.commit()
    conn.close()
    print("[SEARCH][DB_SETUP] ✅ Schema and FTS triggers ready.")

import sqlite3
from app.config import settings

DB_PATH = settings.database_url.replace("sqlite:///", "")

def ensure_fts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS ocr_index
        USING fts5(video_id, frame_path, ocr_text);
    """)

    cur.executescript("""
        DROP TRIGGER IF EXISTS ocr_frames_ai;
        DROP TRIGGER IF EXISTS ocr_frames_ad;
        DROP TRIGGER IF EXISTS ocr_frames_au;

        CREATE TRIGGER IF NOT EXISTS ocr_frames_ai
        AFTER INSERT ON ocr_frames
        BEGIN
            INSERT INTO ocr_index(video_id, frame_path, ocr_text)
            VALUES (new.video_id, new.frame_path, new.ocr_text);
        END;

        CREATE TRIGGER IF NOT EXISTS ocr_frames_ad
        AFTER DELETE ON ocr_frames
        BEGIN
            DELETE FROM ocr_index WHERE frame_path = old.frame_path;
        END;

        CREATE TRIGGER IF NOT EXISTS ocr_frames_au
        AFTER UPDATE ON ocr_frames
        BEGIN
            UPDATE ocr_index
            SET ocr_text = new.ocr_text
            WHERE frame_path = old.frame_path;
        END;
    """)

    conn.commit()
    conn.close()
    print("[SEARCH][FTS] ✅ FTS index and triggers ensured for ocr_frames table.")



def search_text(query: str):
    """Perform a full-text search with context snippets."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("""
        SELECT video_id, frame_path,
               snippet(ocr_index, -1, '<mark>', '</mark>', '...', 15) AS snippet
        FROM ocr_index
        WHERE ocr_index MATCH ?
        ORDER BY rank LIMIT 50;
    """, (query,))

    results = [dict(row) for row in cur.fetchall()]
    conn.close()
    return results

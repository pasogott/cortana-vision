# app/utils/indexer.py
import sqlite3
import time
from app.config import settings

DB_PATH = settings.database_url.replace("sqlite:///", "")

# ------------------------------------------------------
# 🔒 Enforce FTS uniqueness
# ------------------------------------------------------
def enforce_unique_index():
    """Ensure each frame_path appears only once in ocr_index."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create a helper metadata table to track unique frame paths
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ocr_index_meta (
            frame_path TEXT PRIMARY KEY
        );
    """)

    # Insert only missing paths from ocr_index into the meta table
    cur.execute("""
        INSERT OR IGNORE INTO ocr_index_meta (frame_path)
        SELECT frame_path FROM ocr_index;
    """)

    # Delete duplicates in ocr_index that aren't the first occurrence
    cur.executescript("""
        DELETE FROM ocr_index
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM ocr_index
            GROUP BY frame_path
        );
        VACUUM;
    """)

    conn.commit()
    conn.close()
    print("[FTS][UNIQUE] ✅ Deduplicated ocr_index and enforced uniqueness via ocr_index_meta.")


# ------------------------------------------------------
# ✅ Ensure FTS5 Table and Triggers (self-healing)
# ------------------------------------------------------
def ensure_fts():
    """Ensure the ocr_index FTS5 table and its triggers exist and are valid."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Drop legacy/broken triggers (rowid-based or duplicates)
    cur.executescript("""
        DROP TRIGGER IF EXISTS ocr_ai;
        DROP TRIGGER IF EXISTS ocr_ad;
        DROP TRIGGER IF EXISTS ocr_au;
        DROP TRIGGER IF EXISTS ocr_frames_ai;
        DROP TRIGGER IF EXISTS ocr_frames_ad;
        DROP TRIGGER IF EXISTS ocr_frames_au;
    """)

    # 2) Check if ocr_index exists and is a VIRTUAL TABLE fts5
    cur.execute("SELECT type, sql FROM sqlite_master WHERE name='ocr_index';")
    row = cur.fetchone()
    needs_recreate = False
    if not row:
        needs_recreate = True
    else:
        t, sql = row
        # wrong kind OR wrong module (not fts5) -> recreate
        if t != "table":
            # For virtual tables, sqlite_master.type is "table"; we must inspect SQL text
            pass
        if not sql or "VIRTUAL TABLE" not in sql.upper() or "FTS5" not in sql.upper():
            needs_recreate = True

    if needs_recreate:
        print("[FTS][FIX] Dropping broken/missing ocr_index and re-creating as FTS5…")
        cur.execute("DROP TABLE IF EXISTS ocr_index;")
        conn.commit()
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ocr_index
            USING fts5(video_id, frame_path, ocr_text);
        """)

    # 3) Recreate sane triggers (no rowid usage; keep in sync)
    cur.executescript("""
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

    # 4) Rebuild if empty
    cur.execute("SELECT COUNT(*) FROM ocr_index;")
    count = cur.fetchone()[0]
    if count == 0:
        print("[FTS][REBUILD] Re-indexing from ocr_frames…")
        cur.execute("""
            INSERT INTO ocr_index(video_id, frame_path, ocr_text)
            SELECT video_id, frame_path, ocr_text FROM ocr_frames;
        """)
        print("[FTS][REBUILD] ✅ ocr_index rebuilt from existing data.")

    conn.commit()
    conn.close()
    print("[SEARCH][FTS] ✅ FTS index and triggers ensured for ocr_frames table.")
    enforce_unique_index()

# ------------------------------------------------------
# 🔍 Full-Text Search
# ------------------------------------------------------
def search_text(query: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT video_id, frame_path,
                   snippet(ocr_index, -1, '<mark>', '</mark>', '...', 15) AS snippet
            FROM ocr_index
            WHERE ocr_index MATCH ?
            ORDER BY rank
            LIMIT 50;
        """, (query,))
        res = [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"[FTS][ERR] Search failed: {e}")
        res = []
    conn.close()
    return res

# ------------------------------------------------------
# 🧱 Update Index (with retries)
# ------------------------------------------------------
def update_index(frame_key: str, retries: int = 5, delay: float = 0.8):
    """Reindex a single OCRFrame entry into FTS with retries and backoff."""
    for attempt in range(1, retries + 1):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT video_id, ocr_text FROM ocr_frames WHERE frame_path = ?", (frame_key,))
        row = cur.fetchone()
        conn.close()

        if row:
            video_id, ocr_text = row
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO ocr_index (video_id, frame_path, ocr_text)
                VALUES (?, ?, ?);
            """, (video_id, frame_key, ocr_text))
            conn.commit()
            conn.close()
            print(f"[SEARCH] ✅ Indexed {frame_key} (attempt {attempt})")
            return True

        print(f"[SEARCH][WAIT] OCRFrame not ready for {frame_key} (attempt {attempt}/{retries})")
        time.sleep(delay * attempt)

    print(f"[SEARCH][WARN] No OCRFrame found for {frame_key} after {retries} retries.")
    return False

# ------------------------------------------------------
# ♻️ Background Reindexer (finds gaps and fixes them forever)
# ------------------------------------------------------
def background_reindex():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("""
                SELECT f.frame_path
                FROM ocr_frames f
                LEFT JOIN ocr_index i ON f.frame_path = i.frame_path
                WHERE i.frame_path IS NULL
                LIMIT 50;
            """)
            missing = [r[0] for r in cur.fetchall()]
            conn.close()

            if missing:
                print(f"[FTS][FIX] Found {len(missing)} missing frames, reindexing…")
                for key in missing:
                    update_index(key)
            time.sleep(15)
        except Exception as e:
            print(f"[FTS][ERR] Background reindexer crashed: {e}")
            time.sleep(10)

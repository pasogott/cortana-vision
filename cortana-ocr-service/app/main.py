from app.worker import listen_for_jobs
from app.utils.db_integrity import ensure_integrity

if __name__ == "__main__":
    print("[INIT] 🧩 Running DB initialization and integrity checks…")
    ensure_integrity()
    print("[INIT] ✅ Database ready and consistent.")
    print("[OCR] 🚀 Starting OCR worker…")
    listen_for_jobs()

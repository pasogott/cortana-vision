from app.worker import listen_for_jobs

if __name__ == "__main__":
    print("[OCR] 🚀 Starting OCR worker…")
    listen_for_jobs()

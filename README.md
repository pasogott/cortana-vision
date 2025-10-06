🦅 Snapshot Sandbox – Eagle Vision OCR Platform

Snapshot Sandbox is a full-stack FastAPI + OpenCV + Tesseract application that extracts, analyzes, and searches text from video frames.
It was built for scene-level OCR, fast search across frames, and visual navigation through a simple UI.

⚙️ Tech Stack
Layer	Tools
Backend	FastAPI (Uvicorn + async HTTP client httpx)
Computer Vision / OCR	OpenCV + Tesseract (pytesseract)
Database	SQLite (via SQLAlchemy ORM)
Storage	Hetzner S3 (Object Storage) with boto3
Tasking	FastAPI BackgroundTasks for non-blocking OCR
Frontend (UI)	Jinja2 + PicoCSS (lightweight CSS framework)
Containerization	Docker + Docker Compose
Package Manager	uv for fast dependency installs
🧩 Architecture Overview
            ┌──────────────┐
 Upload →   │ /upload      │ ──► saves to /uploads
            └──────────────┘
                     │
                     ▼
             ┌─────────────┐
 Extract →   │ /extract    │ ──► FFmpeg → keyframes → S3 + DB records
             └─────────────┘
                     │
                     ▼
     Background ─►   │ /ocr       │ ──► downloads frames → OpenCV + Tesseract
                     │             │     dual-pass OCR → updates DB
                     ▼
             ┌─────────────┐
 Search →    │ /search     │ ──► query OCR text (fuzzy matching)
             └─────────────┘
                     │
                     ▼
             ┌─────────────┐
 UI →        │ /ui/*       │ ──► HTML pages (index, progress, results, search)
             └─────────────┘

🧠 OCR Pipeline (OpenCV + Tesseract)

Goal: robust recognition of light + dark UI text, usernames, and faint overlays.

Step-by-Step

Frame Fetch

Each video frame is downloaded from Hetzner S3 (via boto3).

Pre-processing (OpenCV)

Convert BGR → grayscale

Invert if dark (mean < 127)

Enhance contrast with CLAHE

Denoise (fastNlMeansDenoising)

Sharpen (using kernel filter)

Adaptive threshold for binary mask

Dual-Pass OCR (Tesseract)

Pass #1: grayscale enhanced (lang=deu+eng)

Pass #2: raw color (lang=eng)

Merge and normalize text → clean whitespace + symbols

Persistence

Each frame’s OCR result → Frame.ocr_content

Flag greyscale_is_processed = True

Searchability

Fuzzy search (difflib.SequenceMatcher) supports typos and partial matches like tania ≈ tanja1976

🧱 Database Schema
Table	Key Fields	Description
Video	id (UUID), filename, path, is_processed, is_processed_datetime_utc	Tracks each uploaded video
Frame	id (UUID), video_id, path, frame_number, frame_time, ocr_content, greyscale_is_processed	Stores frames + OCR results
📦 Environment Variables (.env)
APP_NAME=Snapshot Sandbox – Eagle Vision
ENVIRONMENT=development
DEBUG=True

DATABASE_URL=sqlite:////app/data/snapshot.db

# Hetzner S3 (Storage)
S3_URL=
S3_BUCKET=cyberheld
S3_ACCESS_KEY=
S3_SECRET_KEY=
REGION=nbg1
STORAGE_PROVIDER=

UPLOAD_DIR=
KEYFRAME_DIR=

🐳 Docker Setup

Dockerfile installs:

ffmpeg (for scene detection)

tesseract-ocr

OpenCV libraries (libsm6, libxext6, etc.)

uv for fast Python installs

docker build -t snapshot-api .
docker compose up --build


Visit → http://localhost:8000/ui/

🚀 Endpoints Summary
Category	Route	Description
Upload	POST /upload	Save video to uploads/
Extract	POST /extract?filename=X&threshold=0.08	Use FFmpeg scene detection → frames → S3
	GET /extract/status/{filename}	Check scene extraction progress
OCR	POST /ocr?video_id=UUID	Launch background OCR task
	GET /ocr/status/{video_id}	Track OCR progress (% complete)
Search	GET /search?q=term&video_id=UUID	Search OCR results (fuzzy)
Debug	GET /debug/db	Inspect videos & frame counts
UI	/ui/	Main index (upload → extract → search)
	/ui/progress	OCR/extraction progress page
	/ui/results	Search results grid
	/ui/search	Interactive search portal (HTML + AJAX)
🖥 UI Pages (Templates)
Template	Description
index.html	Main dashboard: upload video, start processing workflow
progress.html	Live polling of extraction and OCR status (% done)
results.html	Search results grid with frame thumbs + snippets
search.html	Stand-alone AJAX search interface with video selector
🎨 Features

Responsive PicoCSS layout

Dynamic dropdown populated from /debug/db

AJAX calls → /search

Realtime progress polling for background OCR

Image grid with snippet hover info

🧪 Example Testing Flow

Upload

curl -F "file=@'Screen Recording 2025-09-29 at 09.34.00.mov'" http://localhost:8000/upload


Extract Keyframes

curl -X POST "http://localhost:8000/extract/?filename=Screen%20Recording%202025-09-29%20at%2009.34.00.mov&threshold=0.08"


→ returns video_id

Run OCR (background)

curl -X POST "http://localhost:8000/ocr/?video_id=<video_id>"


→ use /ocr/status/<video_id> to check progress

Search

curl -G "http://localhost:8000/search" --data-urlencode "q=tanja1976" --data-urlencode "video_id=<video_id>"


Visual Review

Open http://localhost:8000/ui/search to interactively browse results

🧮 Internal Optimizations
Feature	Description
Background OCR	Non-blocking OCR via BackgroundTasks so API remains responsive
Scene Extraction	FFmpeg scene detection + histogram based frame selection
Image Pre-processing	CLAHE contrast + denoise + adaptive threshold for UI text
Fuzzy Search	Handles partial and approximate matches (tolerant of typos)
S3 Integration	Uploads frames and builds signed URLs for UI rendering
UI Routing	Dedicated HTML routes under /ui/* (fully decoupled from API)
🧭 Navigation Flow
/ui/                → upload video
└── /ui/progress    → see keyframe/OCR progress
    └── /ui/results → view extracted OCR matches
        └── /ui/search → deep search / handle queries

🧰 Developer Notes

FFmpeg tuning: adjust threshold (0.05–0.1) to control scene sensitivity.

OCR languages: edit lang="deu+eng" in ocr.py to add more language packs.

SQLite exploration:

docker exec -it snapshot-api uv pip install sqlite-utils
docker exec -it snapshot-api sqlite3 /app/data/snapshot.db ".tables"


Logs:

OCR progress logged in container stdout every 25 frames.

/ocr/status/{video_id} returns percent completion.

✅ Features Summary

🎥 Upload videos

✂️ Automatic scene detection and keyframe extraction

☁️ Frame upload to Hetzner S3

🧠 Dual-pass OCR processing (OpenCV + Tesseract)

🔍 Fuzzy text search across frames

💡 Responsive HTML UI (front + backend integrated)

🧱 SQLite database tracking for frames + videos

🚀 Asynchronous background OCR task execution

🔄 Progress tracking and results dashboard

🏁 Conclusion

Snapshot Sandbox – Eagle Vision is a complete, containerized micro-pipeline for video → frame → text → search workflows.
It demonstrates:

scalable OCR processing,

intelligent frame extraction,

smooth async architecture,

and a friendly UI for visual inspection.

You can deploy it standalone, connect it to larger microservices (e.g., api-gateway-service), or extend it for multi-tenant agent use in Kuuka.
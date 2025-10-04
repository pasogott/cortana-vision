# 🧩 Snapshot Sandbox

A lightweight FastAPI service for **scene-change detection** in screen recordings.
It extracts only the frames where something visibly changes — ideal for building searchable, OCR-ready datasets from video.

---

## 🚀 1. Setup Environment

Clone or copy this repository, then open it in your terminal:

```bash
cd snapshot-sandbox
Create and activate a Python virtual environment:

Mac / Linux

bash
Copy code
python3 -m venv venv
source venv/bin/activate
Windows

bash
Copy code
python -m venv venv
venv\Scripts\activate
📦 2. Install Dependencies
Install requirements from requirements.txt:

bash
Copy code
pip install -r requirements.txt
Make sure ffmpeg is installed on your system:

Mac (Homebrew):

bash
Copy code
brew install ffmpeg
Ubuntu/Debian:

bash
Copy code
sudo apt install ffmpeg
Windows:

Download from https://ffmpeg.org/download.html

Add ffmpeg to your system PATH.

🧠 3. Run the Server
Start the FastAPI server:

bash
Copy code
uvicorn main:app --reload --port 8000
You should see:

nginx
Copy code
Uvicorn running on http://127.0.0.1:8000
Test that it’s alive:

Visit http://localhost:8000/docs for Swagger UI

Or run:

bash
Copy code
curl http://localhost:8000/
🎥 4. Upload a Video
bash
Copy code
curl -X 'POST' \
  'http://localhost:8000/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@Screen Recording 2025-09-29 at 09.34.00.mov;type=video/quicktime'
✅ Response:

json
Copy code
{
  "status": "success",
  "filename": "Screen Recording 2025-09-29 at 09.34.00.mov",
  "path": "uploads/Screen Recording 2025-09-29 at 09.34.00.mov"
}
🧩 5. Extract Scene Changes
Run scene detection with chosen sensitivity (lower = more sensitive):

bash
Copy code
curl -X 'POST' \
  'http://localhost:8000/extract-scenes?filename=Screen%20Recording%202025-09-29%20at%2009.34.00.mov&threshold=0.08' \
  -H 'accept: application/json'
🧠 Explanation:

threshold=0.08 — detects small scrolls or content changes

Outputs frames to:

swift
Copy code
keyframes/Screen Recording 2025-09-29 at 09.34.00/
📁 6. View Results
After a few seconds, check your project folder:

yaml
Copy code
snapshot-sandbox/
 ├── uploads/
 │    └── Screen Recording 2025-09-29 at 09.34.00.mov
 ├── keyframes/
 │    └── Screen Recording 2025-09-29 at 09.34.00/
 │         ├── frame_0001.jpg
 │         ├── frame_0002.jpg
 │         └── ...
 └── main.py
Each image represents a point in the video where something new appeared on screen.
Perfect for downstream OCR or timeline indexing.

🧹 7. Reset Workspace
To clear all extracted frames and uploads:

bash
Copy code
rm -rf uploads keyframes
🧠 Next Step
Add a /index endpoint to generate a timestamp → frame JSON index

Integrate OCR or frontend preview (optional)

🛠 Requirements Recap
Component	Purpose	Version
Python	Runtime	≥3.9
FastAPI	Web framework	Latest
Uvicorn	ASGI server	Latest
ffmpeg	Frame extraction	System-level tool

```

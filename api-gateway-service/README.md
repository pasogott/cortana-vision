🚀 1. Setup Environment

Clone the repository and navigate into it:

```bash
git clone git@github.com:pasogott/cortana-vision.git
cd api-gateway-service
```

Install dependencies using uv

uv handles virtual environments and dependency resolution automatically:

```bash
uv sync
```

💡 This creates a local .venv and installs all dependencies from pyproject.toml.

📦 2. Run the Server

Start the FastAPI app via uvicorn through uv:

```bash
uv run uvicorn main:app --reload --app-dir src
```

You should see output similar to:

```bash
INFO:     Will watch for changes in these directories: ['src']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Test the API
• Open http://localhost:8000/docs for the Swagger UI
• Or test via terminal:

```bash
curl http://localhost:8000/
```

🎥 3. Upload a Video

Send a screen recording for processing:

```bash
curl -X 'POST' \
  'http://localhost:8000/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@Screen Recording 2025-09-29 at 09.34.00.mov;type=video/quicktime'
```

✅ Response

```bash
{
  "status": "success",
  "filename": "Screen Recording 2025-09-29 at 09.34.00.mov",
  "path": "uploads/Screen Recording 2025-09-29 at 09.34.00.mov"
}
```

🧩 4. Extract Scene Changes

Trigger scene detection with a chosen threshold (lower = more sensitive):

```bash
curl -X 'POST' \
  'http://localhost:8000/extract-scenes?filename=Screen%20Recording%202025-09-29%20at%2009.34.00.mov&threshold=0.08' \
  -H 'accept: application/json'
```

    •	threshold=0.08 — detects even subtle scrolls or content changes.
    •	Frames are written to:

```bash
keyframes/Screen Recording 2025-09-29 at 09.34.00/
```

📁 5. View Results

After processing, your folder will look like this:

```bash
api-gateway-service/
 ├── uploads/
 │    └── Screen Recording 2025-09-29 at 09.34.00.mov
 ├── keyframes/
 │    └── Screen Recording 2025-09-29 at 09.34.00/
 │         ├── frame_0001.jpg
 │         ├── frame_0002.jpg
 │         └── ...
 └── src/
      └── main.py
```

Each image represents a frame where something on screen visibly changed —
perfect for OCR and downstream video indexing.

🧹 6. Reset Workspace

To clean up all uploads and extracted frames:

```bash
rm -rf uploads keyframes
```

🧠 Next Steps
• Add an /index endpoint to return a JSON map of timestamps → frame filenames
• Integrate OCR (e.g. Tesseract) to extract on-screen text
• Add a frontend preview or dashboard for visual inspection

⸻

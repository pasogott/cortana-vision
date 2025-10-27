from fastapi import FastAPI, UploadFile
from app.ocr import extract_text
import tempfile

app = FastAPI(title="DeepSeek OCR Service")

@app.post("/ocr")
async def run_ocr(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp.flush()
        text = extract_text(tmp.name)
    return {"text": text}

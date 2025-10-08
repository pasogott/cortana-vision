import os, re, uuid, cv2, pytesseract, numpy as np, asyncio, tempfile
from redis import Redis
from botocore.exceptions import ClientError
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import OCRFrame
from app.utils.s3_utils import download_from_s3

init_db()
redis = Redis.from_url(settings.redis_url, decode_responses=True)

def preprocess_image(local_path: str):
    img = cv2.imread(local_path)
    if img is None:
        raise ValueError("Image not found or unreadable.")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if np.mean(gray) < 127:
        gray = cv2.bitwise_not(gray)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)
    bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                               cv2.THRESH_BINARY, 17, 8)
    return bw

def perform_ocr(image):
    config = "--oem 3 --psm 6 -c preserve_interword_spaces=1"
    try:
        text = pytesseract.image_to_string(image, lang="deu+eng", config=config)
    except pytesseract.TesseractError:
        text = pytesseract.image_to_string(image, lang="eng", config=config)
    return re.sub(r"\s+", " ", text.strip())

def process_frame(key: str):
    tmp_file = os.path.join(settings.tmp_dir, f"{uuid.uuid4()}.jpg")
    try:
        download_from_s3(key, tmp_file)
        img = preprocess_image(tmp_file)
        text = perform_ocr(img)
        db = SessionLocal()
        rec = OCRFrame(video_id=key.split("/")[1], frame_path=key, ocr_text=text, is_processed=True)
        db.add(rec)
        db.commit()
        db.close()
        print(f"[OCR] ✅ Processed {key}")
        redis.publish("cortana-events", f"ocr-index-updated:{key}")
    except ClientError as e:
        print(f"[OCR][ERR] S3 issue: {e}")
    except Exception as e:
        print(f"[OCR][ERR] Failed to process {key}: {e}")
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

def listen_for_jobs():
    sub = redis.pubsub()
    sub.subscribe(settings.jobs_channel)
    print(f"[OCR] 🧠 Listening for '{settings.event_ocr}' on {settings.jobs_channel}...")
    for msg in sub.listen():
        if msg["type"] == "message":
            data = msg["data"]
            if data.startswith(settings.event_ocr):
                key = data.split(":", 1)[-1]
                process_frame(key)

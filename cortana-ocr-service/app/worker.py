import os, re, uuid, cv2, pytesseract, numpy as np, traceback
from redis import Redis
from botocore.exceptions import ClientError
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import OCRFrame, Frame, Video
from app.utils.s3_utils  import download_from_s3
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import json

# ---------- Initialization ----------
init_db()
redis = Redis.from_url(settings.redis_url, decode_responses=True)

LANGS = "deu+eng"
TMP_DIR = settings.tmp_dir

# Force environment variable — Docker is authoritative
os.environ["TESSDATA_PREFIX"] = "/usr/share/tesseract-ocr/5/tessdata"
print(f"[OCR][INIT] ✅ Forced TESSDATA_PREFIX={os.environ['TESSDATA_PREFIX']}")



# ---------- Ensure Tesseract Path ----------
if not os.getenv("TESSDATA_PREFIX"):
    for path in DEFAULT_TESSDATA_DIRS:
        if os.path.exists(os.path.join(path, "eng.traineddata")):
            os.environ["TESSDATA_PREFIX"] = os.path.dirname(path)
            print(f"[OCR][INIT] ✅ TESSDATA_PREFIX set to {os.environ['TESSDATA_PREFIX']}")
            break
    else:
        print("[OCR][WARN] ⚠️ Could not find traineddata path! OCR may fail.")
else:
    print(f"[OCR][INIT] 🧠 Using pre-set TESSDATA_PREFIX={os.environ['TESSDATA_PREFIX']}")


# ---------- Helpers ----------
def preprocess_image(local_path: str):
    """Load and clean up image for OCR."""
    img = cv2.imread(local_path)
    if img is None:
        raise ValueError(f"Image not found or unreadable: {local_path}")

    # Grayscale + invert if dark
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if np.mean(gray) < 127:
        gray = cv2.bitwise_not(gray)

    # Contrast enhancement + denoise + sharpen
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.fastNlMeansDenoising(gray, None, 25, 7, 21)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    gray = cv2.filter2D(gray, -1, sharpen_kernel)

    # Adaptive threshold
    bw = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        17, 8
    )
    return bw


def perform_ocr(image):
    """Run OCR with fallback to English."""
    config = "--oem 3 --psm 6 -c preserve_interword_spaces=1"

    try:
        text = pytesseract.image_to_string(image, lang=LANGS, config=config)
    except pytesseract.TesseractError as e:
        print(f"[OCR][WARN] Multi-language OCR failed ({LANGS}): {e}")
        try:
            text = pytesseract.image_to_string(image, lang="eng", config=config)
        except pytesseract.TesseractError as e2:
            print(f"[OCR][FATAL] English fallback failed: {e2}")
            raise RuntimeError("Tesseract could not load any language models.")
    return re.sub(r"\s+", " ", text.strip())


# ---------- Core OCR Logic ----------
def process_frame(key: str):
    """Download, OCR, store, and update video progress (race-safe)."""
    tmp_file = os.path.join(TMP_DIR, f"{uuid.uuid4()}.jpg")
    db = SessionLocal()
    try:
        # --- Download & preprocess ---
        download_from_s3(key, tmp_file)
        img = preprocess_image(tmp_file)
        text = perform_ocr(img)

        # --- Extract video_id + a best-effort filename ---
        parts = key.split("/")
        video_id = parts[1] if len(parts) > 1 else parts[0]
        best_filename = parts[1] if len(parts) > 2 else key.split("/")[-3] if len(parts) >= 3 else "unknown.mp4"

        # --- Ensure parent video exists BEFORE ocr_frames insert ---
        video = db.query(Video).filter_by(id=video_id).first()
        if not video:
            video = Video(
                id=video_id,
                filename=best_filename,
                status="processing",
                is_processed=False,
            )
            db.add(video)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()  # parent might have been created concurrently
                video = db.query(Video).filter_by(id=video_id).first()

        # --- Upsert OCR result (race-safe) ---
        record = db.query(OCRFrame).filter_by(frame_path=key).first()
        if record:
            record.ocr_text = text
            record.is_processed = True
            db.commit()
        else:
            db.add(OCRFrame(
                video_id=video_id,
                frame_path=key,
                ocr_text=text,
                is_processed=True,
            ))
            try:
                db.commit()
            except IntegrityError:
                # Another insert won the race -> convert to UPDATE
                db.rollback()
                db.query(OCRFrame).filter_by(frame_path=key).update(
                    {"ocr_text": text, "is_processed": True}
                )
                db.commit()

        print(f"[OCR] ✅ Processed {key} (text length={len(text)})")

        # --- Mark video ready if all frames processed ---
        total_frames = db.query(Frame).filter_by(video_id=video_id).count()
        done_frames = db.query(OCRFrame).filter_by(video_id=video_id, is_processed=True).count()

        if total_frames > 0 and done_frames >= total_frames:
            video = db.query(Video).filter_by(id=video_id).first()
            if video:
                video.status = "ready"
                video.is_processed = True
                db.commit()
                print(f"[OCR] 🎉 Video {video.filename} marked READY ({done_frames}/{total_frames})")

        # --- Notify search/index service ---
        import json
        redis.publish(
            settings.events_channel,
            json.dumps({"event": settings.event_ocr_update, "key": key})
        )

    except ClientError as e:
        print(f"[OCR][ERR][S3] {e}")
    except Exception as e:
        print(f"[OCR][ERR] {key}: {e}\n{traceback.format_exc()}")
    finally:
        db.close()
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

# ---------- Redis Listener ----------
def listen_for_jobs():
    sub = redis.pubsub()
    sub.subscribe(settings.jobs_channel)
    print(f"[OCR] 🧠 Listening for '{settings.event_ocr}' on channel '{settings.jobs_channel}'...")

    while True:
        try:
            msg = sub.get_message(ignore_subscribe_messages=True, timeout=2)
            if not msg:
                continue

            raw = msg.get("data")
            if not raw:
                continue

            # ---- Parse message (handle both JSON + legacy) ----
            event, key = None, None
            if isinstance(raw, str):
                try:
                    payload = json.loads(raw)
                    event = payload.get("event")
                    key = (
                        payload.get("payload", {}).get("frame_s3_key")
                        or payload.get("key")
                        or payload.get("path")
                    )
                except json.JSONDecodeError:
                    if ":" in raw:
                        parts = raw.split(":", 1)
                        event, key = parts[0].strip(), parts[1].strip()
                    else:
                        print(f"[OCR][WARN] ⚠️ Unrecognized message: {raw}")
                        continue

            print(f"[OCR][DEBUG] Received event='{event}' key='{key}'")

            # ---- Process only matching event ----
            if event == settings.event_ocr and key:
                print(f"[OCR][JOB] 🧩 Dispatching → {key}")
                process_frame(key)
            else:
                print(f"[OCR][IGNORE] Event '{event}' (expected '{settings.event_ocr}')")

        except Exception as e:
            print(f"[OCR][ERR] Listener crashed → {e}\n{traceback.format_exc()}")
            try:
                init_db()
                ensure_integrity()
                print("[OCR][HEAL] ✅ Database integrity rechecked.")
            except Exception as db_err:
                print(f"[OCR][HEAL][FAIL] Could not heal DB → {db_err}")
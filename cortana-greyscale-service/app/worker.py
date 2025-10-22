import os, cv2, json, uuid, time, shutil, traceback
from datetime import datetime
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, Base, engine
from app.models import Frame, Video
from app.utils.s3_utils import upload_to_s3, download_from_s3
from app.utils.pubsub_utils import publish_event

# Ensure DB tables exist
Base.metadata.create_all(bind=engine, checkfirst=True)

async def make_greyscale_from_samples(payload: dict, redis: Redis):
    """
    Convert a sampled frame to greyscale and queue for OCR.
    - Downloads frame from S3
    - Converts to greyscale
    - Uploads to /greyscaled/ path
    - Updates DB
    - Publishes JSON OCR job payload
    """
    t0 = time.time()
    video_id = payload.get("video_id")
    frame_s3_key = payload.get("frame_s3_key")
    frame_url = payload.get("frame_url")
    frame_number = payload.get("frame_number")

    print(f"\n[GREYSCALE] 🔔 Received → frame_{frame_number} from {video_id}")

    db: Session = SessionLocal()
    try:
        # --- Create tmp workspace
        os.makedirs(settings.tmp_dir, exist_ok=True)
        local_path = os.path.join(settings.tmp_dir, f"{uuid.uuid4()}.jpg")

        # --- 1️⃣ Download source frame
        download_from_s3(frame_s3_key, local_path)

        # --- 2️⃣ Convert to greyscale
        img = cv2.imread(local_path)
        if img is None:
            print(f"[GREYSCALE][ERR] Empty or unreadable image for frame {frame_number}")
            return

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_path = os.path.join(settings.tmp_dir, f"gray_{uuid.uuid4()}.jpg")
        cv2.imwrite(gray_path, gray)

        # --- 3️⃣ Upload to /greyscaled/ folder on S3
        grey_key = frame_s3_key.replace("/samples/", "/greyscaled/")
        grey_url = upload_to_s3(gray_path, grey_key)

        # --- 4️⃣ Update DB record
        frame = db.scalar(
            select(Frame).where(
                Frame.video_id == video_id,
                Frame.frame_number == frame_number
            )
        )
        if frame:
            frame.greyscale_is_processed = True
            frame.path = grey_url
            db.commit()
        else:
            print(f"[GREYSCALE][WARN] Frame record missing in DB for {video_id}:{frame_number}")

        print(f"[GREYSCALE] ✅ frame_{frame_number} processed → {grey_url}")

        # --- 5️⃣ Publish OCR job (JSON format)
        publish_event(redis, settings.jobs_channel, settings.event_ocr, grey_key)
        print(f"[GREYSCALE] 🧩 Published OCR job → {grey_key}")

    except Exception as e:
        db.rollback()
        print(f"[GREYSCALE][ERR] Crash → {e}\n{traceback.format_exc()}")

    finally:
        db.close()
        # --- 6️⃣ Cleanup temporary files
        for path in [local_path, gray_path]:
            if os.path.exists(path):
                os.remove(path)

        print(f"[GREYSCALE] 🧹 Done in {round(time.time()-t0,2)}s")

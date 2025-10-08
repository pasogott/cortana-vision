import os, cv2, json, uuid, time, shutil
from datetime import datetime
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal, Base, engine
from app.models import Frame, Video
from app.utils.s3_utils import upload_to_s3, download_from_s3

Base.metadata.create_all(bind=engine, checkfirst=True)

async def make_greyscale_from_samples(payload: dict, redis: Redis):
    """Convert sampled frame to greyscale and push to OCR queue."""
    t0 = time.time()
    video_id = payload.get("video_id")
    frame_s3_key = payload.get("frame_s3_key")
    frame_url = payload.get("frame_url")
    frame_number = payload.get("frame_number")
    print(f"\n[GREYSCALE] 🔔 Received → frame_{frame_number} from {video_id}")

    db: Session = SessionLocal()
    try:
        os.makedirs(settings.tmp_dir, exist_ok=True)
        local_path = os.path.join(settings.tmp_dir, f"{uuid.uuid4()}.jpg")

        # 1️⃣ Download from S3
        download_from_s3(frame_s3_key, local_path)

        # 2️⃣ Convert to greyscale
        img = cv2.imread(local_path)
        if img is None:
            print(f"[GREYSCALE][ERR] Empty image for frame {frame_number}")
            return

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray_path = os.path.join(settings.tmp_dir, f"gray_{uuid.uuid4()}.jpg")
        cv2.imwrite(gray_path, gray)

        # 3️⃣ Upload to S3 (grayscale folder)
        grey_key = frame_s3_key.replace("/samples/", "/greyscaled/")
        grey_url = upload_to_s3(gray_path, grey_key)

        # 4️⃣ Update DB
        frame = db.scalar(select(Frame).where(Frame.video_id == video_id, Frame.frame_number == frame_number))
        if frame:
            frame.greyscale_is_processed = True
            frame.path = grey_url
            db.commit()
        print(f"[GREYSCALE] ✅ frame_{frame_number} processed → {grey_url}")

        # 5️⃣ Publish OCR job
        msg = {
            "event": settings.event_ocr,
            "payload": {
                "video_id": video_id,
                "frame_s3_key": grey_key,
                "frame_url": grey_url,
                "frame_number": frame_number
            },
        }
        redis.publish(settings.jobs_channel, f"{settings.event_ocr}:{grey_key}")

        # 6️⃣ Cleanup
        os.remove(local_path)
        os.remove(gray_path)
        print(f"[GREYSCALE] 🧹 Done in {round(time.time()-t0,2)}s")

    except Exception as e:
        db.rollback()
        print(f"[GREYSCALE][ERR] Crash → {e}")
    finally:
        db.close()

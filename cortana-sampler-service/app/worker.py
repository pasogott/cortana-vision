import asyncio, os, cv2, json, shutil, subprocess, uuid, time
from datetime import datetime
from typing import List
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, SessionLocal, Base
from app.models import Video, Frame
from app.utils.s3_utils import upload_to_s3, download_from_s3

# ------------------------------------------------------------
# 1️⃣  Ensure schema exists
# ------------------------------------------------------------
Base.metadata.create_all(bind=engine, checkfirst=True)


# ------------------------------------------------------------
# 2️⃣  Helper functions
# ------------------------------------------------------------
def _ffmpeg_extract_scenes(video_path: str, out_dir: str, threshold: float) -> List[str]:
    """Extract keyframes where scene changes exceed threshold."""
    os.makedirs(out_dir, exist_ok=True)
    log_path = os.path.join(out_dir, "scene_log.txt")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"select=gt(scene\\,{threshold}),showinfo",
        "-vsync", "vfr",
        os.path.join(out_dir, "frame_%04d.jpg"),
    ]
    with open(log_path, "w") as log:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=log, check=False)

    frames = sorted([f for f in os.listdir(out_dir) if f.lower().endswith(".jpg")])
    return [os.path.join(out_dir, f) for f in frames]


def _deduplicate_by_hist(paths: List[str]) -> List[str]:
    """Drop near-identical frames using histogram correlation."""
    kept, prev_hist = [], None
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        if prev_hist is not None:
            diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
            if diff < 0.97:
                kept.append(p)
                prev_hist = hist
        else:
            kept.append(p)
            prev_hist = hist
    return kept


# ------------------------------------------------------------
# 3️⃣  Core worker logic
# ------------------------------------------------------------
async def make_samples_from_video(payload: dict, redis: Redis):
    """
    Handles a 'make-samples-from-video' job.
    payload = { "video_id": "...", "filename": "..." }
    """
    t0 = time.time()
    video_id = payload.get("video_id")
    filename = payload.get("filename")
    print(f"\n[SAMPLER] 🔔 Job received → {video_id} ({filename})")

    db: Session = SessionLocal()
    try:
        # 1️⃣ Verify DB record
        video = db.scalar(select(Video).where(Video.id == video_id))
        if not video:
            print(f"[SAMPLER][ERR] ❌ Video not found in DB → {video_id}")
            return
        print(f"[SAMPLER] ✅ Video found: {video.filename}")

        # 2️⃣ Derive and normalize S3 key
        s3_key = (
            video.path.split(f"{settings.s3_bucket}/")[-1]
            if settings.s3_bucket in video.path else video.path
        )
        if s3_key.startswith(settings.s3_url):
            s3_key = s3_key.split(f"{settings.s3_bucket}/", 1)[-1]
        print(f"[SAMPLER] S3 Key: {s3_key}")

        # 3️⃣ Download video locally
        os.makedirs(settings.tmp_dir, exist_ok=True)
        tmp_video = os.path.join(settings.tmp_dir, f"{video_id}.mp4")
        try:
            download_from_s3(s3_key, tmp_video)
            print(f"[SAMPLER] ⬇️  Downloaded {tmp_video}")
        except Exception as e:
            print(f"[SAMPLER][ERR] Download failed → {e}")
            return

        # 4️⃣ Extract & deduplicate keyframes
        out_dir = os.path.join(settings.tmp_dir, f"samples_{video_id}")
        all_frames = _ffmpeg_extract_scenes(tmp_video, out_dir, settings.sample_threshold)
        kept = _deduplicate_by_hist(all_frames)
        print(f"[SAMPLER] 🎞️  Kept {len(kept)}/{len(all_frames)} frames")

        if not kept:
            print("[SAMPLER][WARN] No keyframes extracted; skipping job")
            return

        # 5️⃣ Upload frames + save to DB + prepare greyscale jobs
        uploaded = 0
        base_prefix = f"videos/{video_id}/samples"

        for idx, local_frame in enumerate(kept, start=1):
            try:
                key = f"{base_prefix}/frame_{idx:04d}.jpg"
                url = upload_to_s3(local_frame, key)

                frame = Frame(
                    id=str(uuid.uuid4()),
                    video_id=video_id,
                    path=url,
                    frame_number=idx,
                    frame_time=float(idx - 1),
                    greyscale_is_processed=False,
                )
                db.add(frame)
                uploaded += 1

                # ✅ Publish greyscale job (JSON payload)
                greyscale_job = {
                    "event": settings.event_greyscale,
                    "payload": {
                        "video_id": video_id,
                        "frame_number": idx,
                        "frame_s3_key": key,
                        "frame_url": url,
                        "source_service": "sampler-service",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }

                try:
                    redis.publish(settings.jobs_channel, json.dumps(greyscale_job))
                except Exception:
                    # 👇 Ignore non-critical publishing errors
                    print(f"[SAMPLER][WARN] Could not publish job for frame_{idx:04d}")

                if uploaded % 10 == 0 or uploaded == len(kept):
                    print(f"[SAMPLER] ⬆️  Uploaded {uploaded}/{len(kept)} frames and queued jobs")

                await asyncio.sleep(0.001)

            except Exception as e:
                print(f"[SAMPLER][WARN] frame_{idx:04d} upload failed: {e}")

        # 6️⃣ Commit DB updates
        video.is_processed = True
        video.is_processed_datetime_utc = datetime.utcnow()
        db.commit()

        # 7️⃣ Cleanup
        print(f"[SAMPLER] ✅ {uploaded} frames processed. Queued greyscale jobs.")
        shutil.rmtree(out_dir, ignore_errors=True)
        os.remove(tmp_video)
        print(f"[SAMPLER] 🧹 Cleanup complete in {round(time.time() - t0, 2)}s")

    except json.JSONDecodeError:
        # 👇 This is the new fix — safely ignore plain-text Redis messages
        print(f"[SAMPLER] Ignored non-JSON message")
    except Exception as e:
        db.rollback()
        print(f"[SAMPLER][ERR] Crash → {e}")
    finally:
        db.close()

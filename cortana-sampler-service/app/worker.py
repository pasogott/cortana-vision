import asyncio, json, os, shutil, subprocess, tempfile
from typing import List

import cv2
import boto3
from botocore.config import Config
from redis import Redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, declarative_base, mapped_column, Mapped, sessionmaker
from sqlalchemy import String, Float, Boolean, DateTime, Text

from .config import settings

# ---------- DB Models (minimal mirror of your monolith) ----------
Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)  # S3 url of the video
    # other columns exist but we don't need to touch them here

class Frame(Base):
    __tablename__ = "frames"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)  # S3 url of the frame
    frame_number: Mapped[float] = mapped_column(Float, nullable=False)
    frame_time: Mapped[float] = mapped_column(Float, nullable=False)
    greyscale_is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    ocr_content: Mapped[str | None] = mapped_column(Text, nullable=True)

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

# ---------- S3 client (Hetzner compatible) ----------
s3 = boto3.client(
    "s3",
    endpoint_url=settings.s3_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    region_name=settings.region,
    config=Config(s3={"addressing_style": "path"}, signature_version="s3v4"),
)

def upload_to_s3(local_path: str, remote_path: str) -> str:
    s3.upload_file(local_path, settings.s3_bucket, remote_path)
    return f"{settings.s3_url}/{settings.s3_bucket}/{remote_path}"

def download_from_s3(object_key: str, out_path: str) -> None:
    s3.download_file(settings.s3_bucket, object_key, out_path)

# ---------- Core sampling logic ----------
def _ffmpeg_extract_scenes(video_path: str, out_dir: str, threshold: float) -> List[str]:
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
    kept = []
    prev_hist = None
    for p in paths:
        img = cv2.imread(p)
        if img is None:
            continue
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([g], [0], None, [256], [0, 256])
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

async def make_samples_from_video(payload: dict, redis: Redis):
    """
    payload = {
      "video_id": "...",
      "filename": "Screen Recording ... .mov"
    }
    """
    video_id = payload["video_id"]
    filename = payload["filename"]

    with SessionLocal() as db:
        video: Video | None = db.scalar(select(Video).where(Video.id == video_id))
        if not video:
            print(f"[SAMPLER] Video {video_id} not found in DB.")
            return

        # Parse S3 object key from stored video.path
        # Expecting path like https://.../bucket/videos/XYZ.mov  OR  videos/XYZ.mov
        s3_key = video.path.split(f"{settings.s3_bucket}/")[-1] if settings.s3_bucket in video.path else video.path
        if s3_key.startswith(settings.s3_url):
            s3_key = s3_key.split(f"{settings.s3_bucket}/", 1)[-1]

        # Temp download
        os.makedirs(settings.tmp_dir, exist_ok=True)
        tmp_video = os.path.join(settings.tmp_dir, f"{video_id}.mp4")
        download_from_s3(s3_key, tmp_video)

        # Extract scenes
        out_dir = os.path.join(settings.tmp_dir, f"samples_{video_id}")
        all_frames = _ffmpeg_extract_scenes(tmp_video, out_dir, settings.sample_threshold)
        kept = _deduplicate_by_hist(all_frames)
        print(f"[SAMPLER] Kept {len(kept)} samples (from {len(all_frames)}).")

        # Upload + DB rows
        base_prefix = f"videos/{video_id}/samples"
        for idx, local_frame in enumerate(kept, start=1):
            key = f"{base_prefix}/frame_{idx:04d}.jpg"
            url = upload_to_s3(local_frame, key)

            fr = Frame(
                video_id=video_id,
                path=url,
                frame_number=float(idx),
                frame_time=float(idx - 1),
                greyscale_is_processed=False,
            )
            db.add(fr)

            # publish the next-step job per image
            msg = {
                "event": settings.event_greyscale,
                "payload": {
                    "video_id": video_id,
                    "frame_s3_key": key,
                    "frame_url": url,
                    "frame_number": idx
                }
            }
            redis.publish(settings.jobs_channel, json.dumps(msg))

        db.commit()

        # cleanup
        try:
            shutil.rmtree(out_dir, ignore_errors=True)
            os.remove(tmp_video)
        except Exception:
            pass

        print(f"[SAMPLER] Wrote {len(kept)} frames to S3/DB and queued greyscale jobs.")

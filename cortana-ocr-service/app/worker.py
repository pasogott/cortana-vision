import os, re, uuid, cv2, json
from redis import Redis
from easyocr import Reader
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.database import SessionLocal, init_db
from app.models import OCRFrame, Frame, Video
from app.utils.s3_utils import download_from_s3

init_db()
redis = Redis.from_url(settings.redis_url, decode_responses=True)
TMP_DIR = settings.tmp_dir

reader = Reader(['de'], gpu=False)

def enhance(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g,(3,3),0)
    _,t = cv2.threshold(g,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    up = cv2.resize(t,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
    return up

def perform_ocr(image):
    image = enhance(image)
    r = reader.readtext(image, detail=0, paragraph=True)
    t = " ".join(r)
    return re.sub(r"\s+"," ",t.strip())

def process_frame(key):
    if key.startswith("http"): key = key.split(".com/")[-1]
    tmp = os.path.join(TMP_DIR, f"{uuid.uuid4()}.jpg")
    db = SessionLocal()
    try:
        download_from_s3(key, tmp)
        img = cv2.imread(tmp)
        if img is None: raise RuntimeError("bad frame")
        text = perform_ocr(img)
        print(f"[TEXT] {key} -> \"{text}\"")

        p = key.split("/")
        vid = p[1] if len(p)>2 and p[0]=="videos" else p[0]
        fn = p[2] if len(p)>2 else "unknown.mp4"

        v = db.query(Video).filter_by(id=vid).first()
        if not v:
            v = Video(id=vid, filename=fn, status="processing", is_processed=False)
            db.add(v)
            try: db.commit()
            except IntegrityError: db.rollback()

        r = db.query(OCRFrame).filter_by(frame_path=key).first()
        if r:
            r.ocr_text = text; r.is_processed = True
        else:
            db.add(OCRFrame(video_id=vid, frame_path=key, ocr_text=text, is_processed=True))

        try: db.commit()
        except IntegrityError:
            db.rollback()
            db.query(OCRFrame).filter_by(frame_path=key).update({"ocr_text":text,"is_processed":True})
            db.commit()

        total = db.query(Frame).filter_by(video_id=vid).count()
        done = db.query(OCRFrame).filter_by(video_id=vid,is_processed=True).count()
        if total>0 and done>=total:
            v = db.query(Video).filter_by(id=vid).first()
            v.status="ready"; v.is_processed=True; db.commit()

        redis.publish(settings.events_channel,json.dumps({"event":settings.event_ocr_update,"key":key}))
        print(f"[OCR] {key} ({len(text)} chars)")

    except Exception as e:
        print(f"[ERR] {key}: {e}")

    finally:
        db.close()
        if os.path.exists(tmp): os.remove(tmp)

def listen_for_jobs():
    sub = redis.pubsub()
    sub.subscribe(settings.jobs_channel)
    print("[OCR] ready")
    while True:
        m = sub.get_message(ignore_subscribe_messages=True, timeout=2)
        if not m: continue
        raw = m.get("data")
        if not raw: continue
        try:
            p = json.loads(raw)
            ev = p.get("event")
            key = p.get("key") or p.get("path") or p.get("payload",{}).get("frame_s3_key")
        except:
            if ":" in raw: ev,key = raw.split(":",1)
            else: continue
        if ev==settings.event_ocr and key:
            print(f"[JOB] {key}")
            process_frame(key)

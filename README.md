
1️⃣ API-SERVICE
   → Receives upload (multipart/form-data)
   → Saves raw file to S3/local
   → Publishes Redis job: { event: "VIDEO_UPLOADED", video_name, s3_path }

2️⃣ SAMPLER-SERVICE
   → Listens for "VIDEO_UPLOADED"
   → Extracts frames (ffmpeg / OpenCV)
   → Saves frame images to S3/local
   → Emits "FRAMES_EXTRACTED"

3️⃣ GREYSCALE-SERVICE
   → Listens for "FRAMES_EXTRACTED"
   → Converts to grayscale
   → Emits "FRAMES_GREYSCALED"

4️⃣ OCR-SERVICE
   → Listens for "FRAMES_GREYSCALED"
   → Runs pytesseract
   → Emits "OCR_COMPLETED"

# Hetzner S3 Bucket – cortana-vision

## Purpose

Hetzner’s S3-compatible object storage is the **single source of truth for all video files and derived media**.  
Every uploaded screen recording is stored here and referenced by its unique `video.id` in the database.  
Workers use signed URLs for safe, time-limited access.

---

## Bucket Structure

We recommend one bucket per environment (e.g. `cortana-vision-prod`, `cortana-vision-staging`).  
Inside the bucket, objects are organized by **video UUID**.

```
cortana-vision-prod/
├─ videos/
│   ├─ original/{video_id}/master.mp4        # original upload
│   ├─ proxy/{video_id}/index.m3u8           # HLS proxy / transcoded streams
│   └─ clips/{video_id}/{clip_id}.mp4        # on-demand search-result clips
├─ frames/
│   └─ {video_id}/{timestamp_ms}.jpg         # keyframes for OCR
├─ thumbs/
│   └─ {video_id}/poster.jpg                 # poster / preview thumbnails
└─ logs/
└─ pipeline/{job_id}.json                # optional: processing logs
```

**Key points**

-   **Folder names** are only logical prefixes; the bucket remains flat at S3 level.
-   Every object path always contains the `video_id` to simplify cleanup and cascade deletion.

---

## Access and Security

### Credentials

-   Generate a dedicated **Access Key / Secret** in Hetzner Cloud Console.
-   Store these as Kubernetes secrets or Supabase env vars:

```
S3_ENDPOINT=https://.digitaloceanspaces.com   # Hetzner endpoint
S3_BUCKET=cortana-vision-prod
S3_ACCESS_KEY_ID=…
S3_SECRET_ACCESS_KEY=…
```

### Principle of Least Privilege

-   The bucket policy allows only the service account to **read/write** objects.
-   Public access is never enabled.
-   All public downloads (e.g., preview clips) use **presigned URLs** that expire after a short time.

### Recommended Settings

-   Versioning: optional (useful for audit/rollback of derived assets).
-   Lifecycle rules:
-   Keep `clips/` objects only for a limited time (e.g., 30 days) to save storage.
-   Move old `frames/` to cheaper cold storage if not frequently re-OCRed.

---

## How Services Use the Bucket

| Service                  | Action                                                                                                 |
| ------------------------ | ------------------------------------------------------------------------------------------------------ |
| **S3 Cron Scanner**      | Detects newly uploaded original videos and inserts a `videos` + `jobs` record.                         |
| **Transcode Worker**     | Reads from `videos/original/…`, writes HLS proxies to `videos/proxy/…`, and generates thumbnails.      |
| **Sampler Worker**       | Reads proxy or original video to produce keyframes (`frames/…`).                                       |
| **OCR Worker**           | Reads keyframes, writes OCR debug artifacts (optional).                                                |
| **Segment-Index Worker** | Pure DB work – no direct S3 writes.                                                                    |
| **Clip Service**         | Creates short on-demand clips and uploads them to `videos/clips/…`.                                    |
| **API Gateway**          | Issues short-lived **presigned URLs** so the frontend can stream or download without exposing S3 keys. |

---

## Typical Object Lifecycle

1. **Upload** – A raw screen recording is uploaded to `videos/original/{video_id}/master.mp4`.
2. **Transcode** – The transcode worker writes HLS/MP4 proxies and thumbnails.
3. **Sampling & OCR** – Frames extracted to `frames/{video_id}/…` and processed.
4. **On-demand clips** – Created dynamically and stored under `videos/clips/{video_id}/`.
5. **Cleanup/Archival** – Lifecycle rules or explicit jobs can remove frames or old clips.

---

## Best Practices

-   Use **UUIDs** (not human names) for `video_id` and `clip_id` to avoid collisions.
-   Rely on **database relationships** for deletion:  
    deleting a `video` in Postgres triggers workers to delete all related S3 objects.
-   Keep bucket-wide list operations minimal; let the DB drive cleanup.

---

## Monitoring & Costs

-   Enable **access logs** to monitor traffic and audit access.
-   Track **storage class usage** and apply lifecycle policies for cost optimization.

---

By following this layout, cortana-vision maintains a **secure, auditable, and clean object store** that can scale with thousands of long, high-fps videos.

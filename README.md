# Cortana – Video OCR & Search

Cortana is a self-hosted backend that turns high-framerate social-media screen recordings into a fully searchable knowledge base.
It detects every piece of on-screen text (including emojis, @handles, hashtags, numbers) and links it to precise video timestamps so you can instantly jump to any matching moment.

## 🚀 Tech Stack

| Layer / Service          | Technology / Image                  | Purpose                                                                 |
|--------------------------|---------------------------------------|-------------------------------------------------------------------------|
| **API Gateway**          | Python (FastAPI) – `cortana-api`     | REST/GraphQL API, JWT auth, search queries, presigned S3 URLs, job dispatch |
| **S3 Cron Scanner**      | Python – `cortana-s3-scanner`        | Detects new videos in Hetzner S3 and creates initial processing jobs   |
| **Transcode Worker**     | Python + FFmpeg – `cortana-transcode`| Generates HLS/proxy versions and thumbnails                             |
| **Sampler Worker**       | Python + FFmpeg – `cortana-sampler`  | Downsamples video (~10–15 fps), detects frame changes (pHash/dHash)    |
| **OCR Worker**           | Python + OCR (e.g. Tesseract) – `cortana-ocr` | Detects and recognizes on-screen text, emojis, hashtags                 |
| **Segment-Index Worker** | Python – `cortana-segment-index`     | Merges identical texts, extracts entities, updates full-text indexes    |
| **Clip Service**         | Python + FFmpeg – `cortana-clip`     | Creates on-demand short video clips around search hits                   |
| **Database & Auth**      | Supabase (PostgreSQL)               | Stores videos, OCR segments, entities and handles authentication         |
| **Object Storage**       | Hetzner S3                           | Stores original videos, frames, thumbnails, generated clips              |
| **Container Platform**   | Kubernetes                            | Deploys all Cortana services as Deployments/CronJobs with HPA & secrets |
| **Frontend**             | Next.js                                | Google-style search UI and video playback                                |
| **Reverse Proxy**        | Caddy                                  | TLS termination, routing, Basic Auth for Studio                          |



## 🏗️ Processing Pipeline

Cortana runs as several containerized services inside Kubernetes.
Each new video is automatically ingested and processed in well-defined stages:
	1.	Ingest & Detection
	•	s3-cron-scanner notices new uploads in Hetzner S3.
	•	Inserts metadata into Supabase and creates a transcode job.
	2.	Transcode
	•	transcode-worker creates HLS/proxy versions and thumbnails for fast preview.
	3.	Sampling & Change Detection
	•	sampler-worker down-samples from 120 fps to ~10–15 fps.
	•	Uses perceptual hashing to skip duplicate or unchanged frames.
	•	**Must use original high-resolution video files** (not proxy versions) to ensure maximum quality for OCR processing.
	4.	Text Detection & OCR
	•	ocr-worker reads only the significant frames/clips extracted from original videos.
	•	Detects multi-language text and emojis, storing each snippet with t_start and t_end.
	5.	Segment & Index
	•	segment-index-worker merges consecutive identical texts, extracts entities (@/#/URLs), and updates Supabase’s full-text/trigram indexes.
	6.	Search & Clip Generation
	•	api-gateway provides REST/GraphQL endpoints for keyword search.
	•	clip-service generates short, context-rich video clips on demand.

`Upload → Transcode → Sample → OCR → Segment/Index → Search/Clip`

## 🔎 Key Features
	•	Multi-language OCR with emoji and hashtag support
	•	Precise minute/second timestamps for every detected text
	•	Fast full-text and fuzzy search via Supabase/PostgreSQL
	•	Automatic scaling and fault tolerance with Kubernetes
	•	On-demand video clip generation for search hits

## 📂 Repository

cortana-vision contains:
	•	Kubernetes manifests and Dockerfiles for all services
	•	Supabase schema and migration files
	•	Deployment and scaling instructions

## Folder Structure
```
cortana-vision/
│
├─ services/                           # every microservice is a standalone Python/uv project
│   ├─ api-gateway/
│   │   ├─ pyproject.toml
│   │   ├─ uv.lock
│   │   ├─ src/cortana_api/...
│   │   └─ Dockerfile
│   │
│   ├─ s3-cron-scanner/
│   │   ├─ pyproject.toml
│   │   ├─ uv.lock
│   │   ├─ src/cortana_s3_scanner/...
│   │   └─ Dockerfile
│   │
│   ├─ transcode-worker/
│   │   ├─ pyproject.toml
│   │   ├─ uv.lock
│   │   ├─ src/cortana_transcode/...
│   │   └─ Dockerfile
│   │
│   ├─ sampler-worker/
│   │   ├─ pyproject.toml
│   │   ├─ uv.lock
│   │   ├─ src/cortana_sampler/...
│   │   └─ Dockerfile
│   │
│   ├─ ocr-worker/
│   │   ├─ pyproject.toml
│   │   ├─ uv.lock
│   │   ├─ src/cortana_ocr/...
│   │   └─ Dockerfile
│   │
│   ├─ segment-index-worker/
│   │   ├─ pyproject.toml
│   │   ├─ uv.lock
│   │   ├─ src/cortana_segment_index/...
│   │   └─ Dockerfile
│   │
│   └─ clip-service/
│       ├─ pyproject.toml
│       ├─ uv.lock
│       ├─ src/cortana_clip/...
│       └─ Dockerfile
│
├─ deploy/                              # Kubernetes manifests
│   ├─ base/                             # namespace, common ConfigMaps/Secrets
│   ├─ prod/                             
│   │   ├─ api-gateway/
│   │   ├─ s3-cron-scanner/
│   │   ├─ transcode-worker/
│   │   ├─ sampler-worker/
│   │   ├─ ocr-worker/
│   │   ├─ segment-index-worker/
│   │   └─ clip-service/
│   └─ staging/
│
├─ .github/
│   └─ workflows/                        # CI/CD pipelines: build & push Docker image per service (paths filtered)
│
├─ scripts/                               # helper scripts for local dev or CI
│
├─ docs/                                   # architecture diagrams, pipeline docs
│
└─ README.md
```

# 🐳 Cortana-Vision Docker & Deployment Guide

This document explains how to **build, run, and manage** the entire Cortana-Vision system using Docker Compose.

---

## 📦 Overview

Cortana-Vision is a modular AI video-processing platform consisting of **five core microservices** connected via **Redis** and  **SQLite (or PostgreSQL)** . Each container handles a distinct step in the video → frame → OCR → search pipeline.

### 🔧 Service Summary

| Service                                             | Description                                                                   | Port | Depends On       |
| --------------------------------------------------- | ----------------------------------------------------------------------------- | ---- | ---------------- |
| **API Service (`cortana-api`)**             | Entry point for uploading videos. Saves metadata, uploads to S3, queues jobs. | 8000 | Redis            |
| **Sampler Service (`cortana-sampler`)**     | Extracts keyframes from videos and stores them on S3.                         | -    | API, Redis       |
| **Greyscale Service (`cortana-greyscale`)** | Converts extracted frames to greyscale and triggers OCR.                      | -    | Redis, API       |
| **OCR Service (`cortana-ocr`)**             | Runs OCR on greyscale frames, saves text results to DB.                       | -    | Redis, Greyscale |
| **Search Service (`cortana-search`)**       | Builds a searchable index of OCR text; provides web dashboard.                | 8080 | Redis, OCR       |
| **Redis**                                     | Message broker for async inter-service events.                                | 6379 | -                |

---

## ⚙️ 1. Prerequisites

Make sure you have these installed locally or on your server:

```bash
Docker >= 24.0
Docker Compose >= 2.0
Python 3.11+ (for local development)
```

Ensure the following folders exist and are writable:

```bash
mkdir -p data uploads
chmod 777 data uploads
```

If running on Linux, you may also need to fix permissions for SQLite:

```bash
sudo chown -R $USER:$USER data uploads
```

---

## 🧱 2. Build Containers

Build all services:

```bash
docker compose build --no-cache
```

Or build a specific one:

```bash
docker compose build cortana-api
```

---

## 🚀 3. Start the Stack

Run everything in the background:

```bash
docker compose up -d
```

Monitor logs (example):

```bash
docker compose logs -f cortana-api
```

Check all services are up:

```bash
docker ps
```

You should see containers for api, sampler, greyscale, ocr, search, and redis.

---

## 🌐 4. Access Points

| Service     | URL                                                       | Description                               |
| ----------- | --------------------------------------------------------- | ----------------------------------------- |
| API Docs    | [http://localhost:8000/docs](http://localhost:8000/docs)     | FastAPI Swagger UI for uploads            |
| Dashboard   | [http://localhost:8080](http://localhost:8080/)              | Web UI for searching processed video text |
| Healthcheck | [http://localhost:8000/health](http://localhost:8000/health) | Simple API health test (if implemented)   |

If deployed on a remote server, replace `localhost` with your server IP (e.g. `http://167.235.203.43:8000`).

---

## 🧩 5. Environment Variables

Example `.env` for API and worker services:

```bash
DATABASE_URL=sqlite:////app/data/snapshot.db
REDIS_URL=redis://cortana-redis:6379/0
S3_URL=https://your-s3-endpoint
S3_BUCKET=cortana-bucket
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
REGION=eu-central-1
TMP_DIR=/app/tmp
MODE=dev
```

> ⚠️ Do **not** commit real credentials — use `.env.example` for reference only.

---

## 🧠 6. Service Responsibilities

### 🧩 API Service (`cortana-api-service`)

* Receives uploaded videos via `/upload` endpoint.
* Saves to S3 and DB.
* Publishes `make-samples-from-video` job to Redis.

### 🎞️ Sampler Service (`cortana-sampler-service`)

* Extracts keyframes using `ffmpeg` and histogram deduplication.
* Uploads each frame to S3.
* Queues greyscale conversion jobs.

### ⚫ Greyscale Service (`cortana-greyscale-service`)

* Downloads frames → converts to grayscale.
* Uploads back to S3 under `/greyscaled/` prefix.
* Triggers OCR job via Redis.

### 🔠 OCR Service (`cortana-ocr-service`)

* Downloads grayscale frame.
* Performs OCR using Tesseract (German + English).
* Saves extracted text to DB.
* Publishes reindex events to Search service.

### 🔍 Search Service (`cortana-search-service`)

* Builds SQLite FTS index for OCR results.
* Provides `/dashboard` and `/search` routes with HTML templates.

---

## 🧰 7. Development Commands

Restart a single service:

```bash
docker compose restart cortana-ocr
```

Stop all:

```bash
docker compose down
```

Clean and rebuild:

```bash
docker compose down -v --remove-orphans
sudo rm -rf data/* uploads/*
docker compose up -d --build
```

---

## 🧾8. Verification Checklist

✅ `docker ps` shows all containers running.

✅ API responds on port `8000`.

✅ Upload works and queues sampler jobs.

✅ Redis logs show `make-samples-from-video`.

✅ Search dashboard loads results after OCR completes.

---

### 🎯 Conclusion

Once all services start successfully, Cortana-Vision runs fully automated:

> Upload video → Sampler extracts → Greyscale converts → OCR reads → Search indexes → Dashboard ready.

You can monitor progress live via Docker logs or Redis events.

---

**Author:** Sam

**Last Updated:** October 2025

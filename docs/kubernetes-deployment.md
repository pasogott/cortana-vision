# Kubernetes Deployment – cortana-vision

## Overview

cortana-vision runs as a set of independent Docker services on a Kubernetes cluster.  
Each service (API, workers, cron jobs) is deployed as its own **Deployment** or **CronJob**,  
with Supabase and Caddy providing database/auth and HTTPS routing.

---

## Components

| Type        | Services                                                                                      |
| ----------- | --------------------------------------------------------------------------------------------- |
| Deployments | api-gateway, ocr-worker, transcode-worker, sampler-worker, segment-index-worker, clip-service |
| CronJob     | s3-cron-scanner                                                                               |
| External    | Supabase (PostgreSQL & auth), Hetzner S3 bucket, Caddy reverse proxy                          |

---

## Secrets & Configuration

-   Store DB credentials, S3 keys, and Supabase JWT/service keys as **Kubernetes Secrets**.
-   Common non-sensitive settings (e.g. logging level) go into ConfigMaps.

---

## Deployment Steps

1. **Build & Push Images**  
   GitHub Actions build and tag Docker images in GHCR whenever service code changes.
2. **Apply Base Resources**  
   Create the namespace and secrets:
    ```bash
    kubectl apply -f deploy/base/
    ```
3. **Deploy Services**  
   Apply manifests for each service:
    ```bash
    kubectl apply -f deploy/prod/api-gateway/
    ```
4. Ingress & TLS
   Caddy acts as the HTTPS entry point and routes to the cluster.

⸻

Scaling & Updates
• Each service is independent and can scale horizontally via HorizontalPodAutoscaler.
• Rolling updates pull the latest tagged images with zero downtime.

⸻

Operations
• Logs are available with kubectl logs.
• Database backups and S3 lifecycle rules handle persistence and retention.
• The full configuration lives in Git for reproducible deployments.

⸻

Summary
Every cortana-vision microservice is its own Deployment/CronJob.
Secrets are injected via Kubernetes, builds and updates are automated via GitHub Actions,
and Caddy provides a single HTTPS endpoint to the outside world.

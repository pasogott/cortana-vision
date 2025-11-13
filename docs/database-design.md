# Database Design – cortana-vision

## Goal
Store and index every visible text element from high-framerate social-media
screen recordings so that each snippet can be **searched and played back at
its exact video timestamp**.

## Key Principles
- **Time-based** – every text record is linked to start and end times inside the video.
- **Search-optimized** – prepared for fast full-text and fuzzy search.
- **Modular** – clean separation of video metadata, OCR segments, extracted entities, and processing jobs.
- **Secure** – Row Level Security (RLS) ensures each user or team sees only their own data.

## Core Tables
| Table                  | Purpose |
|------------------------|---------|
| **videos**            | Master record for each uploaded video with metadata, S3 locations, and processing status |
| **jobs**              | Tracks all processing tasks (ingest, transcode, OCR …) with state and timestamps |
| **segments**          | Stores merged OCR text snippets with language, confidence, and precise time ranges |
| **entities**          | Holds structured items extracted from text (hashtags, mentions, URLs, emojis, numbers) |
| **search_materialized** | Pre-joined, materialized view for lightning-fast search across videos and segments |

## Relationships
videos 1 ── * jobs
videos 1 ── * segments 1 ── * entities

- **videos** is the central anchor for all processing and search.
- **jobs** logs each pipeline step.
- **segments** contains detected and normalized text snippets.
- **entities** captures special tokens inside those segments.

## Table Details

### videos
- Identifiers for owner (user/team)
- Metadata: platform (Facebook, Instagram, TikTok), resolution, FPS, duration
- S3 paths for original and proxy (HLS) files
- Processing state (new / processing / ready)
- Creation and update timestamps

### jobs
- Links back to a video
- Job type and status with retry counts and optional payload
- Records when each step started and finished

### segments
- Connects to video and owner/team
- Stores both raw and normalized text, language code, OCR confidence
- Time interval inside the video (start and end in milliseconds)
- Optional bounding box (x, y, width, height) for on-screen position
- Hash to identify repeated text across frames
- Indexed for full-text and trigram similarity search

### entities
- Structured extracts from segments: `@mentions`, `#hashtags`, URLs, emojis, numeric values
- Normalized values for grouping and filtering
- Useful for analytics and quick lookups

### search_materialized (materialized view)
- Combines `videos` and `segments` for ultra-fast keyword or fuzzy search
- Can be refreshed on a schedule or triggered after OCR batches

## Security & Multi-Tenant Model
- Each core table carries `owner_id` and optional `team_id`
- **Row Level Security** (RLS) policies ensure users and teams only see their own videos and derived data
- Backend workers use a **service role key** to insert and update data while respecting RLS rules for reads

## Typical Processing Flow
1. **Upload detection** – new videos appear in S3 and are recorded in `videos`
2. **Job creation** – pipeline enqueues transcode, sampler, OCR and indexing jobs in `jobs`
3. **OCR results** – detected text is stored in `segments`; entities like hashtags or URLs go into `entities`
4. **Search** – the materialized view powers instant full-text and fuzzy search with jump-to-moment playback

## Design Benefits
- Clear separation of metadata, OCR content, and search indexes
- High query performance even on large archives
- Easy to extend with new entity types or processing stages
- Built-in, secure multi-tenant access control for users and teams

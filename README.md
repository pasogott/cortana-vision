# cortana-vision
Cortana is a self-hosted backend that detects new videos in S3, splits them into frames or clips, runs multi-language OCR (incl. emojis/hashtags), and stores every text snippet with precise timestamps in Supabase/PostgreSQL. A full-text index lets you search and jump to the exact video moment instantly.

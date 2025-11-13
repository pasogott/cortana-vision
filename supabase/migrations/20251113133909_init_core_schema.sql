create extension if not exists "pg_trgm";

create type job_type as enum (
  'transcode',
  'sample',
  'ocr',
  'segment_index',
  'clip_generate'
);

create type job_status as enum (
  'queued',
  'processing',
  'done',
  'failed'
);

create type video_status as enum (
  'new',
  'processing',
  'ready'
);

create type entity_type as enum (
  'mention',
  'hashtag',
  'url',
  'emoji',
  'number'
);

create table videos (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  team_id uuid,
  platform text,
  resolution text,
  fps integer,
  duration integer, -- in seconds
  s3_original_path text not null,
  s3_proxy_path text,
  s3_thumb_path text,
  status video_status not null default 'new',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_videos_owner_id on videos(owner_id);
create index idx_videos_team_id on videos(team_id);
create index idx_videos_status on videos(status);
create index idx_videos_created_at on videos(created_at desc);

alter table videos enable row level security;

create policy "Users can view their own videos"
  on videos for select
  using (auth.uid() = owner_id);

create policy "Users can view team videos"
  on videos for select
  using (team_id is not null and exists (
    select 1 from auth.users
    where auth.uid() = id
  ));

create policy "Users can insert their own videos"
  on videos for insert
  with check (auth.uid() = owner_id);

create policy "Users can update their own videos"
  on videos for update
  using (auth.uid() = owner_id);

create table jobs (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  job_type job_type not null,
  status job_status not null default 'queued',
  retry_count integer not null default 0,
  payload jsonb,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_jobs_video_id on jobs(video_id);
create index idx_jobs_job_type on jobs(job_type);
create index idx_jobs_status on jobs(status);
create index idx_jobs_created_at on jobs(created_at desc);
create index idx_jobs_status_job_type on jobs(status, job_type);

create table segments (
  id uuid primary key default gen_random_uuid(),
  video_id uuid not null references videos(id) on delete cascade,
  owner_id uuid not null,
  team_id uuid,
  text text not null,
  normalized_text text not null,
  text_hash text not null,
  language text,
  confidence real not null check (confidence >= 0 and confidence <= 1),
  t_start integer not null, -- timestamp in milliseconds
  t_end integer not null,   -- timestamp in milliseconds
  bounding_box jsonb,
  created_at timestamptz not null default now()
);

create index idx_segments_video_id on segments(video_id);
create index idx_segments_owner_id on segments(owner_id);
create index idx_segments_team_id on segments(team_id);
create index idx_segments_text_hash on segments(text_hash);
create index idx_segments_t_start on segments(t_start);
create index idx_segments_t_end on segments(t_end);

create index idx_segments_normalized_text_fts on segments using gin(to_tsvector('english', normalized_text));

create index idx_segments_normalized_text_trgm on segments using gin(normalized_text gin_trgm_ops);

alter table segments enable row level security;

create policy "Users can view their own segments"
  on segments for select
  using (auth.uid() = owner_id);

create policy "Users can view team segments"
  on segments for select
  using (team_id is not null and exists (
    select 1 from auth.users
    where auth.uid() = id
  ));

create policy "Service role can insert segments"
  on segments for insert
  with check (true);

create policy "Service role can update segments"
  on segments for update
  using (true);

create table entities (
  id uuid primary key default gen_random_uuid(),
  segment_id uuid not null references segments(id) on delete cascade,
  entity_type entity_type not null,
  value text not null,
  normalized_value text not null,
  created_at timestamptz not null default now()
);

create index idx_entities_segment_id on entities(segment_id);
create index idx_entities_entity_type on entities(entity_type);
create index idx_entities_normalized_value on entities(normalized_value);
create index idx_entities_type_value on entities(entity_type, normalized_value);

alter table entities enable row level security;

create policy "Users can view entities from their segments"
  on entities for select
  using (exists (
    select 1 from segments
    where segments.id = entities.segment_id
    and segments.owner_id = auth.uid()
  ));

create policy "Users can view entities from team segments"
  on entities for select
  using (exists (
    select 1 from segments
    where segments.id = entities.segment_id
    and segments.team_id is not null
  ));

create policy "Service role can insert entities"
  on entities for insert
  with check (true);

create materialized view search_materialized as
select
  s.id as segment_id,
  s.video_id,
  s.owner_id,
  s.team_id,
  s.text,
  s.normalized_text,
  s.text_hash,
  s.language,
  s.confidence,
  s.t_start,
  s.t_end,
  s.bounding_box,
  s.created_at as segment_created_at,
  v.platform,
  v.resolution,
  v.fps,
  v.duration,
  v.s3_original_path,
  v.s3_proxy_path,
  v.s3_thumb_path,
  v.status as video_status,
  v.created_at as video_created_at,
  to_tsvector('english', s.normalized_text) as search_vector
from segments s
join videos v on v.id = s.video_id
where v.status = 'ready';

create index idx_search_mat_video_id on search_materialized(video_id);
create index idx_search_mat_owner_id on search_materialized(owner_id);
create index idx_search_mat_team_id on search_materialized(team_id);
create index idx_search_mat_t_start on search_materialized(t_start);
create index idx_search_mat_search_vector on search_materialized using gin(search_vector);
create index idx_search_mat_normalized_text_trgm on search_materialized using gin(normalized_text gin_trgm_ops);

create or replace function refresh_search_materialized()
returns void
language plpgsql
security definer
as $$
begin
  refresh materialized view concurrently search_materialized;
end;
$$;

create or replace function update_updated_at_column()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger update_videos_updated_at
  before update on videos
  for each row
  execute function update_updated_at_column();

create trigger update_jobs_updated_at
  before update on jobs
  for each row
  execute function update_updated_at_column();

comment on table videos is 'Master records for uploaded videos';
comment on table jobs is 'Asynchronous work queue for video processing pipeline';
comment on table segments is 'OCR-extracted text segments with timestamps';
comment on table entities is 'Structured entities extracted from text segments';
comment on materialized view search_materialized is 'Pre-joined view combining videos and segments for fast search queries';

comment on column videos.status is 'Processing status: new (uploaded), processing (in pipeline), ready (searchable)';
comment on column jobs.job_type is 'Type of processing job: transcode, sample, ocr, segment_index, clip_generate';
comment on column jobs.status is 'Job status: queued, processing, done, failed';
comment on column segments.t_start is 'Start timestamp in milliseconds';
comment on column segments.t_end is 'End timestamp in milliseconds';
comment on column segments.text_hash is 'Hash of normalized text for deduplication';
comment on column segments.confidence is 'OCR confidence score (0.0 to 1.0)';
comment on column entities.entity_type is 'Type of entity: mention (@), hashtag (#), url, emoji, number';

"use client";

import { useEffect, useState, useCallback } from "react";
import type { Summary, VideoList, VideoDetail, FrameList, SearchResult } from "@/lib/searchApi";
import { fetchSummary, fetchVideos, fetchVideo, fetchVideoFrames, searchOCR } from "@/lib/searchApi";

export function useSummary() {
  const [data, setData] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { (async () => {
    try { setData(await fetchSummary()); } catch (e:any) { setErr(e.message); }
    finally { setLoading(false); }
  })(); }, []);
  return { data, loading, err };
}

export function useVideos() {
  const [data, setData] = useState<VideoList | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { (async () => {
    try { setData(await fetchVideos()); } catch (e:any) { setErr(e.message); }
    finally { setLoading(false); }
  })(); }, []);
  return { data, loading, err };
}

export function useVideo(id: string | null) {
  const [data, setData] = useState<VideoDetail | null>(null);
  const [loading, setLoading] = useState(!!id);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { if (!id) return; (async () => {
    setLoading(true);
    try { setData(await fetchVideo(id)); } catch (e:any) { setErr(e.message); }
    finally { setLoading(false); }
  })(); }, [id]);
  return { data, loading, err };
}

export function useFrames(videoId: string | null, limit=100, offset=0, expires_in=900) {
  const [data, setData] = useState<FrameList | null>(null);
  const [loading, setLoading] = useState(!!videoId);
  const [err, setErr] = useState<string | null>(null);
  const reload = useCallback(async () => {
    if (!videoId) return;
    setLoading(true);
    try { setData(await fetchVideoFrames(videoId, { limit, offset, expires_in })); } catch (e:any) { setErr(e.message); }
    finally { setLoading(false); }
  }, [videoId, limit, offset, expires_in]);
  useEffect(() => { reload(); }, [reload]);
  return { data, loading, err, reload };
}

export function useSearch(q: string | null, page=1, page_size=12, expires_in=900) {
  const [data, setData] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const run = useCallback(async () => {
    if (!q) return;
    setLoading(true);
    try { setData(await searchOCR(q, { page, page_size, expires_in })); } catch (e:any) { setErr(e.message); }
    finally { setLoading(false); }
  }, [q, page, page_size, expires_in]);
  useEffect(() => { run(); }, [run]);
  return { data, loading, err, run };
}

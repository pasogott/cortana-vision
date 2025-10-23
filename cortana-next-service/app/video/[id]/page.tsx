"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { fetchVideo, fetchVideoFrames } from "@/lib/searchApi";

function Progress({ value }: { value: number }) {
  return (
    <div className="w-full h-2 bg-blue-100 rounded-full">
      <div className="h-2 bg-blue-600 rounded-full transition-all" style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-blue-100 p-5 shadow-sm">
      <div className="text-sm text-blue-800">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-blue-700">{value}</div>
    </div>
  );
}

export default function VideoDetailPage() {
  const params = useParams<{ id: string }>();
  const q = useSearchParams();
  const router = useRouter();
  const id = params.id;
  const [info, setInfo] = useState<any>(null);
  const [frames, setFrames] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingFrames, setLoadingFrames] = useState(true);
  const [active, setActive] = useState<number | null>(null);
  const page = Number(q.get("page") || 1);
  const pageSize = Number(q.get("page_size") || 24);

  const totalPages = useMemo(() => {
    const total = info?.total_frames ?? 0;
    if (!total || !pageSize) return 1;
    return Math.max(1, Math.ceil(total / pageSize));
  }, [info, pageSize]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr(null);
    fetchVideo(id)
      .then((v) => alive && setInfo(v))
      .catch(() => alive && setErr("Failed to load video"))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id]);

  useEffect(() => {
    let alive = true;
    setLoadingFrames(true);
    const offset = (page - 1) * pageSize;
    fetchVideoFrames(id, { limit: pageSize, offset, expires_in: 900 })
      .then((res) => alive && setFrames(res.items || []))
      .catch(() => alive && setErr("Failed to load frames"))
      .finally(() => alive && setLoadingFrames(false));
    return () => {
      alive = false;
    };
  }, [id, page, pageSize]);

  const onPage = (p: number) => {
    const sp = new URLSearchParams(q.toString());
    sp.set("page", String(p));
    sp.set("page_size", String(pageSize));
    router.push(`/video/${id}?${sp.toString()}`);
    setActive(null);
  };

  const close = useCallback(() => setActive(null), []);
  const prev = useCallback(() => setActive((i) => (i === null ? null : Math.max(0, i - 1))), []);
  const next = useCallback(() => setActive((i) => (i === null ? null : Math.min(frames.length - 1, i + 1))), [frames.length]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (active === null) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "ArrowRight") next();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, close, prev, next]);

  return (
    <main className="min-h-screen bg-white">
      <header className="border-b border-blue-100">
        <div className="mx-auto max-w-6xl px-4 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 hover:bg-blue-50">Dashboard</Link>
            <Link href="/search" className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 hover:bg-blue-50">Search</Link>
          </div>
          <h1 className="text-xl font-semibold text-blue-700">Video Details</h1>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-4 py-8">
        {err && <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div>}

        <div className="rounded-2xl border border-blue-100 p-5 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="min-w-0">
              <div className="text-sm text-blue-800">Filename</div>
              <div className="mt-1 truncate text-blue-900 font-medium">{loading ? "—" : info?.filename || "—"}</div>
              <div className="mt-2 text-xs text-blue-700">ID: {id}</div>
            </div>
            <div className="w-full md:w-1/2">
              <div className="flex items-center gap-3">
                <Progress value={info?.progress ?? 0} />
                <span className="text-blue-900 w-14 text-right">{loading ? "—" : `${info?.progress ?? 0}%`}</span>
              </div>
              <div className="mt-1 text-xs text-blue-700">{loading ? "" : `${info?.processed_frames ?? 0} / ${info?.total_frames ?? 0} frames`}</div>
            </div>
            <div>
              <span className={[
                "inline-flex items-center rounded-full px-3 py-1 text-xs font-medium",
                info?.status === "ready" ? "bg-blue-600 text-white" :
                info?.status === "processing" ? "bg-blue-100 text-blue-800" :
                "bg-blue-50 text-blue-700"
              ].join(" ")}>
                {loading ? "…" : (info?.status || "unknown")}
              </span>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Stat label="Total Frames" value={loading ? "—" : info?.total_frames ?? 0} />
            <Stat label="Processed Frames" value={loading ? "—" : info?.processed_frames ?? 0} />
            <Stat label="Indexed Frames" value={loading ? "—" : info?.indexed_frames ?? info?.processed_frames ?? 0} />
          </div>
        </div>

        <div className="mt-8 rounded-2xl border border-blue-100 p-5 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-blue-700">Frames</h2>
            <div className="text-sm text-blue-800">{loadingFrames ? "Loading…" : `${frames.length} item(s)`}</div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            {frames.map((f, i) => {
              const name = f.filename ?? (f.key ? String(f.key).split("/").pop() : null) ?? `frame_${f.frame_number ?? ""}`;
              return (
                <button
                  type="button"
                  key={`${f.key || f.url}-${f.frame_number ?? i}`}
                  onClick={() => setActive(i)}
                  className="text-left group rounded-xl border border-blue-100 p-3 hover:shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                >
                  <div className="overflow-hidden rounded-lg bg-blue-50">
                    <img
                      src={f.url}
                      alt={name}
                      className="block w-full h-auto transition-transform group-hover:scale-[1.02]"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                    />
                  </div>
                  <div className="mt-3 text-sm text-blue-900 truncate">{name}</div>
                  {!!f.ocr_text && <div className="mt-1 text-xs text-blue-700 line-clamp-2">{f.ocr_text}</div>}
                </button>
              );
            })}
          </div>

          {!loadingFrames && frames.length === 0 && (
            <div className="py-10 text-center text-blue-800">No frames found.</div>
          )}

          <div className="mt-6 flex items-center justify-between">
            <button
              className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 disabled:opacity-50 hover:bg-blue-50"
              onClick={() => onPage(Math.max(1, page - 1))}
              disabled={page <= 1}
            >
              Prev
            </button>
            <div className="text-sm text-blue-900">{page} / {totalPages}</div>
            <button
              className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 disabled:opacity-50 hover:bg-blue-50"
              onClick={() => onPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {active !== null && frames[active] && (
        <div
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={close}
        >
          <div
            className="relative w-full max-w-6xl max-h-[90vh] bg-white rounded-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-blue-100 px-4 py-2">
              <div className="text-sm text-blue-900 truncate">
                {frames[active].filename ?? (frames[active].key ? String(frames[active].key).split("/").pop() : "")}
              </div>
              <button onClick={close} className="rounded-lg px-3 py-1.5 text-blue-700 hover:bg-blue-50">Close</button>
            </div>
            <div className="relative flex items-center justify-center bg-neutral-50">
              <img
                src={frames[active].url}
                alt=""
                className="max-h-[80vh] w-auto h-auto"
                referrerPolicy="no-referrer"
              />
              <button
                onClick={prev}
                disabled={active <= 0}
                className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-white/90 border border-blue-100 px-3 py-2 text-blue-700 disabled:opacity-50"
              >
                ‹
              </button>
              <button
                onClick={next}
                disabled={active >= frames.length - 1}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-white/90 border border-blue-100 px-3 py-2 text-blue-700 disabled:opacity-50"
              >
                ›
              </button>
            </div>
            {!!frames[active].ocr_text && (
              <div className="border-t border-blue-100 p-4 text-sm text-blue-900">
                {frames[active].ocr_text}
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

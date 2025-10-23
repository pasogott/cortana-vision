"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { searchOCR } from "@/lib/searchApi";

export default function SearchPage() {
  const q = useSearchParams();
  const router = useRouter();
  const [query, setQuery] = useState(q.get("q") ?? "");
  const page = Number(q.get("page") || 1);
  const pageSize = Number(q.get("page_size") || 24);

  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const totalPages = useMemo(() => {
    if (!total || !pageSize) return 1;
    return Math.max(1, Math.ceil(total / pageSize));
  }, [total, pageSize]);

  useEffect(() => {
    const initial = q.get("q") ?? "";
    setQuery(initial);
  }, [q]);

  useEffect(() => {
    const current = q.get("q") ?? "";
    if (!current) {
      setItems([]);
      setTotal(0);
      return;
    }
    let alive = true;
    setLoading(true);
    setErr(null);
    searchOCR(current, { page, page_size: pageSize, expires_in: 900 })
      .then((res) => {
        if (!alive) return;
        setItems(res.items || []);
        setTotal(res.total || 0);
      })
      .catch(() => {
        if (!alive) return;
        setErr("Search failed");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [q, page, pageSize]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const sp = new URLSearchParams(q.toString());
    if (query) sp.set("q", query);
    else sp.delete("q");
    sp.set("page", "1");
    sp.set("page_size", String(pageSize));
    router.push(`/search?${sp.toString()}`);
  };

  const onPage = (p: number) => {
    const sp = new URLSearchParams(q.toString());
    sp.set("page", String(p));
    sp.set("page_size", String(pageSize));
    router.push(`/search?${sp.toString()}`);
  };

  return (
    <main className="min-h-screen bg-white">
      <header className="border-b border-blue-100">
        <div className="mx-auto max-w-6xl px-4 py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 hover:bg-blue-50">Dashboard</Link>
            <Link href="/search" className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 hover:bg-blue-50">Search</Link>
          </div>
          <h1 className="text-xl font-semibold text-blue-700">Search</h1>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-4 py-8">
        <form onSubmit={onSubmit} className="flex items-center gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find text inside frames…"
            className="w-full rounded-xl border border-blue-200 px-4 py-2.5 text-blue-950 placeholder-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            className="rounded-xl bg-blue-600 px-4 py-2.5 text-white font-semibold hover:bg-blue-700 active:scale-[.98]"
          >
            Search
          </button>
        </form>

        <div className="mt-4 text-sm text-blue-800">
          {loading ? "Searching…" : (q.get("q") ? `${total} result(s)` : "Type a query and hit Search")}
        </div>

        {err && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{err}</div>
        )}

        {!!items.length && (
          <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            {items.map((it, i) => {
              const name = it.filename ?? (it.key ? String(it.key).split("/").pop() : null) ?? `frame_${it.frame_number ?? ""}`;
              return (
                <Link
                  key={`${it.key || it.url}-${it.frame_number ?? i}`}
                  href={`/video/${it.video_id}`}
                  className="group rounded-xl border border-blue-100 p-3 hover:shadow-sm"
                >
                  <div className="overflow-hidden rounded-lg bg-blue-50">
                    <img
                      src={it.url}
                      alt={name}
                      className="block w-full h-auto transition-transform group-hover:scale-[1.02]"
                      loading="lazy"
                      referrerPolicy="no-referrer"
                    />
                  </div>
                  <div className="mt-3 text-sm text-blue-900 truncate">{name}</div>
                  {!!it.snippet && (
                    <div
                      className="mt-1 text-xs text-blue-700 line-clamp-3"
                      dangerouslySetInnerHTML={{ __html: String(it.snippet) }}
                    />
                  )}
                </Link>
              );
            })}
          </div>
        )}

        {!!items.length && (
          <div className="mt-8 flex items-center justify-between">
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
        )}
      </section>
    </main>
  );
}

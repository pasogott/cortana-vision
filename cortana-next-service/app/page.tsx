"use client";

import Link from "next/link";
import { useSummary, useVideos } from "@/hooks/useSearchApi";

function Progress({ value }: { value: number }) {
  return (
    <div className="w-full h-2 bg-blue-100 rounded-full">
      <div className="h-2 bg-blue-600 rounded-full transition-all" style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} />
    </div>
  );
}

export default function DashboardPage() {
  const { data: summary, loading: loadingSummary, err: errSummary } = useSummary();
  const { data: videos, loading: loadingVideos, err: errVideos } = useVideos();

  return (
    <main className="min-h-screen bg-white">
      <header className="border-b border-blue-100">
        <div className="mx-auto max-w-6xl px-4 py-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold text-blue-700">Dashboard</h1>
          <nav className="flex items-center gap-3">
            <Link href="/search" className="rounded-lg bg-blue-600 px-4 py-2 text-white text-sm font-medium hover:bg-blue-700">Search</Link>
          </nav>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-blue-100 p-5 shadow-sm">
            <div className="text-sm text-blue-800">Total Videos</div>
            <div className="mt-2 text-3xl font-semibold text-blue-700">{loadingSummary ? "—" : summary?.total_videos ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-blue-100 p-5 shadow-sm">
            <div className="text-sm text-blue-800">Total Frames</div>
            <div className="mt-2 text-3xl font-semibold text-blue-700">{loadingSummary ? "—" : summary?.total_frames ?? 0}</div>
          </div>
          <div className="rounded-2xl border border-blue-100 p-5 shadow-sm">
            <div className="text-sm text-blue-800">Indexed Frames</div>
            <div className="mt-2 text-3xl font-semibold text-blue-700">{loadingSummary ? "—" : summary?.indexed_frames ?? 0}</div>
          </div>
        </div>

        {(errSummary || errVideos) && (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errSummary || errVideos}
          </div>
        )}

        <div className="mt-8 rounded-2xl border border-blue-100 p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-blue-700">Videos</h2>
            <span className="text-sm text-blue-800">{loadingVideos ? "Loading…" : `${videos?.items.length ?? 0} item(s)`}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-blue-50 text-blue-800">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Filename</th>
                  <th className="px-4 py-3 text-left font-medium">Frames</th>
                  <th className="px-4 py-3 text-left font-medium">Processed</th>
                  <th className="px-4 py-3 text-left font-medium">Progress</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-left font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {(videos?.items ?? []).map((v: any) => (
                  <tr key={v.id} className="border-t border-blue-100">
                    <td className="px-4 py-3 text-blue-900">{v.filename}</td>
                    <td className="px-4 py-3 text-blue-900">{v.total_frames}</td>
                    <td className="px-4 py-3 text-blue-900">{v.processed_frames}</td>
                    <td className="px-4 py-3 w-64">
                      <div className="flex items-center gap-3">
                        <Progress value={v.progress} />
                        <span className="text-blue-900 w-12 text-right">{v.progress}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={["inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
                        v.status === "ready" ? "bg-blue-600 text-white" :
                        v.status === "processing" ? "bg-blue-100 text-blue-800" :
                        "bg-blue-50 text-blue-700"].join(" ")}>
                        {v.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <a href={`/video/${v.id}`} className="rounded-lg border border-blue-200 px-3 py-1.5 text-blue-700 hover:bg-blue-50">Open</a>
                    </td>
                  </tr>
                ))}
                {!loadingVideos && (videos?.items.length ?? 0) === 0 && (
                  <tr><td className="px-4 py-10 text-center text-blue-800" colSpan={6}>No videos yet.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-8 flex items-center justify-end">
          <a href="/search" className="rounded-lg bg-blue-600 px-4 py-2 text-white text-sm font-medium hover:bg-blue-700">Go to Search</a>
        </div>
      </section>
    </main>
  );
}

export async function getJSON<T>(url: string, qs?: Record<string, any>): Promise<T> {
  const isAbs = /^https?:\/\//i.test(url);
  const base = typeof window === "undefined" ? "http://localhost:3000" : window.location.origin;
  const u = new URL(url, isAbs ? undefined : base);

  if (qs) {
    for (const [k, v] of Object.entries(qs)) {
      if (v !== undefined && v !== null) u.searchParams.set(k, String(v));
    }
  }

  const r = await fetch(u.toString(), {
    method: "GET",
    headers: { Accept: "application/json" },
    credentials: "include",
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

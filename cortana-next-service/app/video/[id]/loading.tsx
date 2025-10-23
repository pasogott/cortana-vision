export default function Loading() {
  return (
    <main className="min-h-screen bg-white">
      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-24 rounded-2xl bg-blue-50" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="h-24 rounded-2xl bg-blue-50" />
            <div className="h-24 rounded-2xl bg-blue-50" />
            <div className="h-24 rounded-2xl bg-blue-50" />
          </div>
          <div className="h-8 w-40 rounded-lg bg-blue-50 mt-8" />
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-40 rounded-xl bg-blue-50" />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

export default function Forbidden() {
  return (
    <main className="page-wrap max-w-3xl">
      <section className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Administration</p>
        <h1 className="mt-1 text-2xl font-semibold text-navy">Access denied</h1>
        <p className="mt-2 text-muted">This page is only for admin accounts.</p>
      </section>
    </main>
  );
}

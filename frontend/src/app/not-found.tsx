import Link from "next/link";

export default function NotFound() {
  return (
    <main className="page-wrap max-w-3xl">
      <section className="page-banner">
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">Not found</p>
        <h1 className="mt-1 text-2xl font-semibold text-navy">This page does not exist</h1>
        <p className="mt-2 text-muted">Check the address, or go back to the home page.</p>
        <Link href="/" className="btn-primary mt-4 w-fit">
          Back to home
        </Link>
      </section>
    </main>
  );
}

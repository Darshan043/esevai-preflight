import Link from "next/link";

export function EmptyState({
  title,
  message,
  actionHref,
  actionLabel,
}: {
  title: string;
  message: string;
  actionHref?: string;
  actionLabel?: string;
}) {
  return (
    <div className="rounded-xl border border-dashed border-zinc-300 bg-white p-6">
      <h2 className="text-xl font-semibold text-zinc-900">{title}</h2>
      <p className="mt-2 text-zinc-600">{message}</p>
      {actionHref && actionLabel ? (
        <Link
          href={actionHref}
          className="mt-4 inline-flex min-h-11 items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

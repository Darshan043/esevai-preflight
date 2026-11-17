// Soft bars shown while a list is still loading.

export function LoadingSkeleton({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      <p className="sr-only">{label}</p>
      <div className="h-28 animate-pulse rounded-2xl bg-sky" />
      <div className="h-28 animate-pulse rounded-2xl bg-sky" />
      <div className="h-28 animate-pulse rounded-2xl bg-sky" />
    </div>
  );
}

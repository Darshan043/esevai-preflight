// Grey bars shown while a list is still loading.

export function LoadingSkeleton({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      <p className="sr-only">{label}</p>
      <div className="h-24 animate-pulse rounded-xl bg-zinc-100" />
      <div className="h-24 animate-pulse rounded-xl bg-zinc-100" />
      <div className="h-24 animate-pulse rounded-xl bg-zinc-100" />
    </div>
  );
}

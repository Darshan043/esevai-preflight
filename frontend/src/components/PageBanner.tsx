export function PageBanner({
  kicker,
  title,
  children,
}: {
  kicker?: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="page-banner">
      {kicker ? (
        <p className="text-xs font-semibold tracking-[0.14em] text-royal uppercase">{kicker}</p>
      ) : null}
      <h1 className="mt-1 text-3xl font-semibold tracking-tight text-navy">{title}</h1>
      {children ? <div className="mt-2 max-w-3xl text-base leading-7 text-muted">{children}</div> : null}
    </header>
  );
}

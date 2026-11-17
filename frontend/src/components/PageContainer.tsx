// Centers page content on the soft portal background.

export function PageContainer({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <main className={`page-wrap ${className}`}>{children}</main>;
}

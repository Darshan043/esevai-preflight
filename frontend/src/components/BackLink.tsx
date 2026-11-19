import Link from "next/link";

export function BackLink({ href, children }: { href: string; children: string }) {
  return (
    <Link href={href} className="inline-flex w-fit text-sm font-semibold text-royal hover:underline">
      ← {children}
    </Link>
  );
}

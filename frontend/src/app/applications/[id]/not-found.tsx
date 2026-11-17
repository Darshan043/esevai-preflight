import Link from "next/link";

import { PageContainer } from "@/components/PageContainer";

export default function ApplicationNotFound() {
  return (
    <PageContainer>
      <h1 className="text-3xl font-semibold text-zinc-900">Application not found</h1>
      <p className="text-zinc-600">We could not find that application on your account.</p>
      <Link
        href="/applications"
        className="inline-flex min-h-11 w-fit items-center rounded-md bg-zinc-900 px-4 text-sm font-medium text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900"
      >
        Back to my applications
      </Link>
    </PageContainer>
  );
}

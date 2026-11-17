import Link from "next/link";

import { PageBanner } from "@/components/PageBanner";
import { PageContainer } from "@/components/PageContainer";

export default function ApplicationNotFound() {
  return (
    <PageContainer>
      <PageBanner kicker="Your account" title="Application not found">
        We could not find that application on your account.
      </PageBanner>
      <Link
        href="/applications"
        className="btn-primary w-fit"
      >
        Back to my applications
      </Link>
    </PageContainer>
  );
}

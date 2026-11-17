import Link from "next/link";

import { PageBanner } from "@/components/PageBanner";
import { PageContainer } from "@/components/PageContainer";

export default function ServiceNotFound() {
  return (
    <PageContainer>
      <PageBanner kicker="Service catalogue" title="Service not found">
        We could not find that service. It may be inactive, or the link may be wrong.
      </PageBanner>
      <Link
        href="/services"
        className="btn-primary w-fit"
      >
        Back to services
      </Link>
    </PageContainer>
  );
}

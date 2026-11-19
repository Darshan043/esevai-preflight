import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PageContainer } from "@/components/PageContainer";

export default function Loading() {
  return (
    <PageContainer>
      <LoadingSkeleton label="Loading page" />
    </PageContainer>
  );
}

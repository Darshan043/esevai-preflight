import { AdminChrome } from "@/app/admin/admin-chrome";
import { requireAdminPage } from "@/app/admin/require-admin";
import { RecentChecksPanel } from "@/components/admin/RecentChecksPanel";

export const instant = false;

export default async function AdminChecksPage() {
  await requireAdminPage();
  return (
    <AdminChrome>
      <RecentChecksPanel />
    </AdminChrome>
  );
}

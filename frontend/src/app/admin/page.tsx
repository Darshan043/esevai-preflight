import { AdminChrome } from "@/app/admin/admin-chrome";
import { requireAdminPage } from "@/app/admin/require-admin";
import { OverviewDashboard } from "@/components/admin/OverviewDashboard";

export const instant = false;

export default async function AdminPage() {
  await requireAdminPage();
  return (
    <AdminChrome>
      <OverviewDashboard />
    </AdminChrome>
  );
}

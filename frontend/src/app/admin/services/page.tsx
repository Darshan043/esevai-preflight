import { AdminChrome } from "@/app/admin/admin-chrome";
import { requireAdminPage } from "@/app/admin/require-admin";
import { ServicesManager } from "@/components/admin/ServicesManager";

export const instant = false;

export default async function AdminServicesPage() {
  await requireAdminPage();
  return (
    <AdminChrome>
      <ServicesManager />
    </AdminChrome>
  );
}

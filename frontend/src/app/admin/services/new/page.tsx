import { AdminChrome } from "@/app/admin/admin-chrome";
import { requireAdminPage } from "@/app/admin/require-admin";
import { ServiceEditor } from "@/components/admin/ServiceEditor";

export const instant = false;

export default async function NewServicePage() {
  await requireAdminPage();
  return (
    <AdminChrome>
      <ServiceEditor />
    </AdminChrome>
  );
}

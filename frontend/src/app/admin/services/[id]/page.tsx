import { AdminChrome } from "@/app/admin/admin-chrome";
import { requireAdminPage } from "@/app/admin/require-admin";
import { ServiceEditor } from "@/components/admin/ServiceEditor";

export const instant = false;

export default async function EditServicePage({ params }: { params: Promise<{ id: string }> }) {
  await requireAdminPage();
  const { id } = await params;
  return (
    <AdminChrome>
      <ServiceEditor serviceId={id} />
    </AdminChrome>
  );
}
